import { defineStore } from 'pinia'
import { computed, reactive, ref } from 'vue'

import { api, call, fetchAll } from '@/api/client'
import { hasStatus } from '@/api/errors'
import type { Block, Page, PageDetail, PageList, PageStatus } from '@/api/types'
import { newestWins } from '@/utils/newest'

import { useJournals } from './journals'

export const PAGE_BATCH = 24
const POLL_MS = 2000

/** Statuses a page leaves on its own, so it's worth asking again. */
export function isBusy(status: PageStatus): boolean {
  return status === 'uploaded' || status === 'transcribing' || status === 'indexing'
}

type View = { journalId: string; status?: PageStatus }
export type PageRef = Pick<Page, 'id' | 'pageNumber'>

function fetchPage(id: string) {
  return call(api.GET('/pages/{pageId}', { params: { path: { pageId: id } } }))
}

/**
 * Pages: everything seen so far by id, the list on screen (one journal, maybe one status), and a
 * poller that follows busy pages until they're ready or failed.
 */
export const usePages = defineStore('pages', () => {
  const byId = reactive(new Map<string, Page>())
  /** What the list on screen shows; null until a journal's first batch is in. */
  const view = ref<View | null>(null)
  const ids = ref<string[]>([])
  const nextCursor = ref<string | null>(null)
  const loading = ref(false)
  const tracked = new Set<string>()
  /** Each journal's pages in order, kept until one is added, moved, renumbered or deleted. */
  const indexes = new Map<string, PageRef[]>()
  const newest = newestWins()
  let timer: ReturnType<typeof setTimeout> | undefined

  const items = computed(() => ids.value.map((id) => byId.get(id)).filter((p) => p !== undefined))

  function inView(page: Page): boolean {
    const current = view.value
    return (
      current !== null &&
      page.journalId === current.journalId &&
      (!current.status || page.status === current.status)
    )
  }

  function keep(page: Page) {
    byId.set(page.id, page)
    if (isBusy(page.status)) track(page.id)
  }

  /** Drops the journal indexes that don't have `page` where it now is. */
  function checkIndexes(page: Page) {
    const before = byId.get(page.id)
    if (before && before.journalId !== page.journalId) indexes.delete(before.journalId)
    const index = indexes.get(page.journalId)
    const listed = index?.some((ref) => ref.id === page.id && ref.pageNumber === page.pageNumber)
    if (index && !listed) indexes.delete(page.journalId)
  }

  /** Stores a page, slots it into the list if it belongs there, and follows it while busy. */
  function put(page: Page) {
    checkIndexes(page)
    keep(page)
    const listed = ids.value.includes(page.id)
    if (!listed && inView(page)) {
      const at = ids.value.findIndex((id) => (byId.get(id)?.pageNumber ?? 0) > page.pageNumber)
      if (at === -1 && nextCursor.value === null) ids.value.push(page.id)
      else if (at !== -1) ids.value.splice(at, 0, page.id)
    } else if (listed && !inView(page)) {
      ids.value = ids.value.filter((id) => id !== page.id)
    }
  }

  /** A page with its blocks. It joins the store, so a busy one is followed. */
  async function fetchDetail(id: string): Promise<PageDetail> {
    const page = await fetchPage(id)
    put(page)
    return page
  }

  /** Saves a block's text or takes back its "not quite sure", and hands back the saved block. */
  async function patchBlock(
    id: string,
    changes: { text?: string; uncertain?: boolean },
  ): Promise<Block> {
    const result = await call(
      api.PATCH('/blocks/{blockId}', { params: { path: { blockId: id } }, body: changes }),
    )
    return result.block
  }

  /** Asks for a fresh reading; the page goes back to "uploaded" and is followed again. */
  async function retranscribe(page: Page) {
    await call(api.POST('/pages/{pageId}/transcribe', { params: { path: { pageId: page.id } } }))
    put({ ...page, status: 'uploaded', error: null })
  }

  /** Deletes a page, then fetches its journal again for the new page count. */
  async function remove(page: Pick<Page, 'id' | 'journalId'>) {
    await call(api.DELETE('/pages/{pageId}', { params: { path: { pageId: page.id } } }))
    forget(page.id)
    void useJournals()
      .refresh(page.journalId)
      .catch(() => {})
  }

  function forget(id: string) {
    const page = byId.get(id)
    if (page) indexes.delete(page.journalId)
    byId.delete(id)
    tracked.delete(id)
    ids.value = ids.value.filter((other) => other !== id)
  }

  function forgetJournal(journalId: string) {
    indexes.delete(journalId)
    for (const page of [...byId.values()]) {
      if (page.journalId === journalId) forget(page.id)
    }
  }

  function fetchBatch(at: View, cursor?: string) {
    return call(
      api.GET('/pages', {
        params: {
          query: { journalId: at.journalId, status: at.status, limit: PAGE_BATCH, cursor },
        },
      }),
    )
  }

  function show(list: PageList, after: string[]) {
    list.items.forEach(keep)
    ids.value = [...after, ...list.items.map((page) => page.id)]
    nextCursor.value = list.nextCursor
  }

  /**
   * Shows a journal's pages, maybe of one status. A new status keeps the old list up until the
   * new one is in, so the grid swaps in one go instead of flashing empty.
   */
  async function load(journalId: string, status?: PageStatus) {
    const current = newest()
    if (view.value?.journalId !== journalId) {
      view.value = null
      ids.value = []
      nextCursor.value = null
    }
    loading.value = true
    try {
      const list = await fetchBatch({ journalId, status })
      if (!current()) return
      view.value = { journalId, status }
      show(list, [])
    } finally {
      if (current()) loading.value = false
    }
  }

  async function more() {
    const at = view.value
    const cursor = nextCursor.value
    if (!at || !cursor || loading.value) return
    const current = newest()
    loading.value = true
    try {
      const list = await fetchBatch(at, cursor)
      if (current()) show(list, ids.value)
    } finally {
      if (current()) loading.value = false
    }
  }

  function track(id: string) {
    tracked.add(id)
    timer ??= setTimeout(poll, POLL_MS)
  }

  // The next round only starts once every answer of this one is in.
  async function poll() {
    const round = [...tracked]
    const answers = await Promise.allSettled(round.map(fetchPage))
    answers.forEach((answer, at) => {
      const id = round[at]!
      if (!tracked.has(id)) return
      if (answer.status === 'fulfilled') {
        put(answer.value)
        if (!isBusy(answer.value.status)) tracked.delete(id)
      } else if (hasStatus(answer.reason, 404)) {
        forget(id)
      }
      // Anything else (offline, a hiccup): ask again next round.
    })
    timer = tracked.size > 0 ? setTimeout(poll, POLL_MS) : undefined
  }

  async function journalIndex(journalId: string): Promise<PageRef[]> {
    const known = indexes.get(journalId)
    if (known) return known
    const pages = await fetchAll((cursor) =>
      call(api.GET('/pages', { params: { query: { journalId, limit: 100, cursor } } })),
    )
    const index = pages.map(({ id, pageNumber }) => ({ id, pageNumber }))
    indexes.set(journalId, index)
    return index
  }

  /** The pages either side of one in its journal, for stepping between neighbours. */
  async function neighbours(
    page: Pick<Page, 'id' | 'journalId'>,
  ): Promise<{ prev?: PageRef; next?: PageRef }> {
    const index = await journalIndex(page.journalId)
    const at = index.findIndex((ref) => ref.id === page.id)
    return at === -1 ? {} : { prev: index[at - 1], next: index[at + 1] }
  }

  return {
    byId,
    view,
    items,
    nextCursor,
    loading,
    put,
    fetchDetail,
    patchBlock,
    retranscribe,
    remove,
    forget,
    forgetJournal,
    load,
    more,
    neighbours,
  }
})
