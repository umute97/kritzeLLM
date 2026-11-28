import { defineStore } from 'pinia'
import { computed, reactive, ref } from 'vue'

import { api, call, fetchAll } from '@/api/client'
import type { Journal } from '@/api/types'

import { usePages } from './pages'
import { useUploads } from './uploads'

export const PER_SHELF = 4

/**
 * The bookshelf. `GET /journals` pages with a cursor and has no total, so the shelf keeps the
 * batches it has seen and only knows whether there's a next one.
 */
export const useJournals = defineStore('journals', () => {
  const shelves = ref<Journal[][]>([])
  const nextCursors = ref<(string | null)[]>([])
  const index = ref(0)
  const loading = ref(false)
  const loaded = ref(false)
  const byId = reactive(new Map<string, Journal>())
  /** Every journal's id in the API's order, once `loadAll()` has fetched them. */
  const allIds = ref<string[]>()

  // Through byId, so a refreshed journal (e.g. its page count after an upload) shows up here too.
  const shelf = computed(() =>
    (shelves.value[index.value] ?? []).map((journal) => byId.get(journal.id) ?? journal),
  )
  const canBack = computed(() => index.value > 0)
  const canNext = computed(() => nextCursors.value[index.value] != null)
  const empty = computed(() => loaded.value && shelves.value[0]?.length === 0)
  const all = computed(() => allIds.value?.flatMap((id) => byId.get(id) ?? []) ?? [])

  function remember(journal: Journal) {
    byId.set(journal.id, journal)
  }

  async function show(at: number) {
    if (shelves.value[at]) {
      index.value = at
      return
    }
    const cursor = at === 0 ? undefined : (nextCursors.value[at - 1] ?? undefined)
    loading.value = true
    try {
      const list = await call(
        api.GET('/journals', { params: { query: { limit: PER_SHELF, cursor } } }),
      )
      list.items.forEach(remember)
      shelves.value[at] = list.items
      nextCursors.value[at] = list.nextCursor
      index.value = at
      loaded.value = true
    } finally {
      loading.value = false
    }
  }

  /** Starts over from the first shelf, e.g. after a journal was added. */
  async function reload() {
    shelves.value = []
    nextCursors.value = []
    allIds.value = undefined
    await show(0)
  }

  const back = () => show(index.value - 1)
  const next = () => show(index.value + 1)

  /** Fetches every journal into `all`, once; adding or deleting one fetches them again. */
  async function loadAll() {
    if (allIds.value) return
    const found = await fetchAll((cursor) =>
      call(api.GET('/journals', { params: { query: { limit: 100, cursor } } })),
    )
    found.forEach(remember)
    allIds.value = found.map((journal) => journal.id)
  }

  /** Fetches a journal afresh, e.g. for its page count after an upload. */
  async function refresh(id: string): Promise<Journal> {
    const journal = await call(
      api.GET('/journals/{journalId}', { params: { path: { journalId: id } } }),
    )
    remember(journal)
    return journal
  }

  async function get(id: string): Promise<Journal> {
    return byId.get(id) ?? refresh(id)
  }

  async function create(name: string, description: string | null): Promise<Journal> {
    const journal = await call(api.POST('/journals', { body: { name, description } }))
    remember(journal)
    await reload()
    return journal
  }

  /** Renames a journal or changes its description. */
  async function update(id: string, changes: { name?: string; description?: string | null }) {
    const journal = await call(
      api.PATCH('/journals/{journalId}', { params: { path: { journalId: id } }, body: changes }),
    )
    remember(journal)
    return journal
  }

  /** Deletes a journal with its pages and its photos still waiting to go up. */
  async function remove(id: string) {
    await call(api.DELETE('/journals/{journalId}', { params: { path: { journalId: id } } }))
    byId.delete(id)
    useUploads().forget(id)
    usePages().forgetJournal(id)
    await reload()
  }

  return {
    shelf,
    index,
    loading,
    loaded,
    empty,
    canBack,
    canNext,
    all,
    byId,
    show,
    reload,
    back,
    next,
    get,
    loadAll,
    refresh,
    create,
    update,
    remove,
  }
})
