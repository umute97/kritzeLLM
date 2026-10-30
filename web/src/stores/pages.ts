import { defineStore } from 'pinia'
import { computed, reactive, ref } from 'vue'

import { api, call } from '@/api/client'
import { ApiError } from '@/api/errors'
import type { Page, PageList, PageStatus } from '@/api/types'

export const PAGE_BATCH = 24
const POLL_MS = 2000

/** Statuses a page leaves on its own, so it's worth asking again. */
export function isBusy(status: PageStatus): boolean {
  return status === 'uploaded' || status === 'transcribing' || status === 'indexing'
}

type View = { journalId: string; status?: PageStatus }

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
  /** Bumped by every list request, so an answer that's been overtaken is dropped. */
  let latest = 0
  let timer: ReturnType<typeof setInterval> | undefined

  const items = computed(() => ids.value.map((id) => byId.get(id)).filter((p) => p !== undefined))

  function inView(page: Page): boolean {
    const current = view.value
    return (
      current !== null &&
      page.journalId === current.journalId &&
      (!current.status || page.status === current.status)
    )
  }

  /** Stores a page, slots it into the list if it belongs there, and follows it while busy. */
  function put(page: Page) {
    byId.set(page.id, page)
    const listed = ids.value.includes(page.id)
    if (!listed && inView(page)) {
      const at = ids.value.findIndex((id) => (byId.get(id)?.pageNumber ?? 0) > page.pageNumber)
      if (at === -1 && nextCursor.value === null) ids.value.push(page.id)
      else if (at !== -1) ids.value.splice(at, 0, page.id)
    } else if (listed && !inView(page)) {
      ids.value = ids.value.filter((id) => id !== page.id)
    }
    if (isBusy(page.status)) track(page.id)
  }

  /** Asks for a fresh reading; the page goes back to "uploaded" and is followed again. */
  async function retranscribe(page: Page) {
    await call(api.POST('/pages/{pageId}/transcribe', { params: { path: { pageId: page.id } } }))
    put({ ...page, status: 'uploaded', error: null })
  }

  function remove(id: string) {
    byId.delete(id)
    tracked.delete(id)
    ids.value = ids.value.filter((other) => other !== id)
  }

  /** Forgets every page of a deleted journal. */
  function forgetJournal(journalId: string) {
    for (const page of [...byId.values()]) {
      if (page.journalId === journalId) remove(page.id)
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
    list.items.forEach((page) => {
      byId.set(page.id, page)
      if (isBusy(page.status)) track(page.id)
    })
    ids.value = [...after, ...list.items.map((page) => page.id)]
    nextCursor.value = list.nextCursor
  }

  /**
   * Shows a journal's pages, maybe of one status. A new status keeps the old list up until the
   * new one is in, so the grid swaps in one go instead of flashing empty.
   */
  async function load(journalId: string, status?: PageStatus) {
    const mine = ++latest
    if (view.value?.journalId !== journalId) {
      view.value = null
      ids.value = []
      nextCursor.value = null
    }
    loading.value = true
    try {
      const list = await fetchBatch({ journalId, status })
      if (mine !== latest) return
      view.value = { journalId, status }
      show(list, [])
    } finally {
      if (mine === latest) loading.value = false
    }
  }

  async function more() {
    const at = view.value
    const cursor = nextCursor.value
    if (!at || !cursor || loading.value) return
    const mine = ++latest
    loading.value = true
    try {
      const list = await fetchBatch(at, cursor)
      if (mine === latest) show(list, ids.value)
    } finally {
      if (mine === latest) loading.value = false
    }
  }

  function track(id: string) {
    tracked.add(id)
    timer ??= setInterval(poll, POLL_MS)
  }

  async function poll() {
    for (const id of [...tracked]) {
      try {
        const page = await call(api.GET('/pages/{pageId}', { params: { path: { pageId: id } } }))
        put(page)
        if (!isBusy(page.status)) tracked.delete(id)
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) remove(id)
        // Anything else (offline, a hiccup): ask again next round.
      }
    }
    if (tracked.size === 0) {
      clearInterval(timer)
      timer = undefined
    }
  }

  /** Every page of a journal in order, for stepping between neighbours. */
  async function journalIndex(journalId: string): Promise<{ id: string; pageNumber: number }[]> {
    const all: { id: string; pageNumber: number }[] = []
    let cursor: string | undefined
    do {
      const list = await call(
        api.GET('/pages', { params: { query: { journalId, limit: 100, cursor } } }),
      )
      all.push(...list.items.map(({ id, pageNumber }) => ({ id, pageNumber })))
      cursor = list.nextCursor ?? undefined
    } while (cursor)
    return all
  }

  return {
    byId,
    view,
    items,
    nextCursor,
    loading,
    put,
    retranscribe,
    remove,
    forgetJournal,
    load,
    more,
    track,
    journalIndex,
  }
})
