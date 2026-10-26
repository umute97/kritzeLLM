import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { ApiError } from '@/api/errors'
import { uploadPage } from '@/api/upload'
import { fileSize } from '@/utils/format'
import { useToasts, type UploadStatus } from '@/ui'

import { useJournals } from './journals'
import { usePages } from './pages'

/** What the API takes (see `PageUpload` in the contract). */
export const MAX_BYTES = 25 * 1024 * 1024
export const MAX_FILES = 100
const TYPES = new Set(['image/jpeg', 'image/png', 'image/heic', 'image/heif', 'image/webp'])
const EXTENSIONS = /\.(jpe?g|png|heic|heif|webp)$/i

export interface UploadRow {
  key: number
  fileName: string
  journalId: string
  /** Set while sending, or for rows that never got a page. */
  own?: { status: UploadStatus; note?: string; statusLabel?: string; progress?: number }
  pageId?: string
  duplicate?: boolean
}

/** Why a file can't go up, or null when it can. */
export function rejectReason(file: File): { label: string; note: string } | null {
  const looksLikePhoto = TYPES.has(file.type) || (file.type === '' && EXTENSIONS.test(file.name))
  if (!looksLikePhoto) return { label: 'Not a photo', note: 'Photos only: JPEG, PNG, HEIC or WebP' }
  if (file.size > MAX_BYTES) {
    return { label: 'Too big', note: `${fileSize(file.size)}, the limit is 25 MB` }
  }
  return null
}

/**
 * Photos on their way into a journal. They go up one at a time (each gets the next free page
 * number, in the order dropped); afterwards each row follows its page through the pages store.
 */
export const useUploads = defineStore('uploads', () => {
  const rows = ref<UploadRow[]>([])
  const queue: { row: UploadRow; file: File }[] = []
  let running = false
  let nextKey = 1

  const pages = usePages()

  function statusOf(row: UploadRow): {
    status: UploadStatus
    note?: string
    statusLabel?: string
    progress?: number
  } {
    if (row.own) return row.own
    const page = row.pageId ? pages.byId.get(row.pageId) : undefined
    // Uploads put their page in the store, so it's only missing once it was deleted.
    if (!page) return { status: 'deleted', note: 'Its page was deleted' }
    const where = `Page ${page.pageNumber}`
    if (row.duplicate) return { status: 'duplicate', note: `Same photo as page ${page.pageNumber}` }
    switch (page.status) {
      case 'uploaded':
        return { status: 'queued', note: `${where} · waiting its turn` }
      case 'transcribing':
        return { status: 'transcribing', note: `${where} · reading the handwriting` }
      case 'indexing':
        return { status: 'indexing', note: `${where} · almost there` }
      case 'ready':
        return { status: 'ready', note: where }
      case 'failed':
        return { status: 'failed', note: page.error?.detail ?? page.error?.title ?? where }
    }
  }

  const shown = computed(() => rows.value.map((row) => ({ ...row, ...statusOf(row) })))

  /** One journal's rows, how they're doing, and whether any are still on their way. */
  function batch(journalId: string) {
    const mine = shown.value.filter((row) => row.journalId === journalId)
    const counts = { done: 0, skipped: 0, failed: 0, deleted: 0, busy: 0 }
    for (const row of mine) {
      if (row.status === 'ready') counts.done++
      else if (row.status === 'duplicate') counts.skipped++
      else if (row.status === 'failed') counts.failed++
      else if (row.status === 'deleted') counts.deleted++
      else counts.busy++
    }
    return { rows: mine, counts, active: counts.busy > 0 }
  }

  /** Adds photos to a journal. Returns a rejection message when none of them can go up. */
  function add(journalId: string, files: File[]): string | null {
    const accepted = files.slice(0, MAX_FILES).filter((file) => !rejectReason(file))
    if (accepted.length === 0) {
      const first = files[0]
      return first
        ? `${first.name} ${rejectReason(first)?.label === 'Too big' ? 'is too big' : 'isn’t a photo'}`
        : null
    }
    for (const file of files.slice(0, MAX_FILES)) {
      const reason = rejectReason(file)
      const row: UploadRow = {
        key: nextKey++,
        fileName: file.name,
        journalId,
        own: reason
          ? { status: 'failed', statusLabel: reason.label, note: reason.note }
          : { status: 'sending', progress: 0, note: `0 KB of ${fileSize(file.size)}` },
      }
      rows.value.push(row)
      if (!reason) queue.push({ row: rows.value.at(-1)!, file })
    }
    void drain()
    return null
  }

  async function drain() {
    if (running) return
    running = true
    const batchJournals = new Set<string>()
    let sent = 0
    while (queue.length) {
      const { row, file } = queue.shift()!
      batchJournals.add(row.journalId)
      try {
        const result = await uploadPage(row.journalId, file, (sent, total) => {
          row.own = {
            status: 'sending',
            progress: Math.round((sent / total) * 100),
            note: `${fileSize(sent)} of ${fileSize(total)}`,
          }
        })
        const item = result.items[0]!
        row.pageId = item.page.id
        row.duplicate = item.duplicate
        row.own = undefined
        if (!item.duplicate) sent++
        pages.put(item.page)
      } catch (error) {
        const problem = error instanceof ApiError ? error.problem : undefined
        row.own = {
          status: 'failed',
          statusLabel: problem?.status === 413 ? 'Too big' : undefined,
          note: problem?.detail ?? problem?.title ?? 'It didn’t go up',
        }
        if (error instanceof ApiError && (error.offline || error.status === 401)) {
          // Everything after it would fail the same way.
          for (const waiting of queue.splice(0)) {
            waiting.row.own = { status: 'failed', note: 'Didn’t go up, try again' }
          }
        }
      }
    }
    running = false
    const journals = useJournals()
    for (const id of batchJournals) void journals.refresh(id).catch(() => {})
    if (sent > 0) {
      useToasts().push({
        tone: 'success',
        title: 'Pages tucked in',
        detail: `${sent === 1 ? '1 photo is' : `${sent} photos are`} on their way in.`,
      })
    }
  }

  /** Clears a journal's batch card once everything in it has settled. */
  function clear(journalId: string) {
    if (batch(journalId).active) return
    rows.value = rows.value.filter((row) => row.journalId !== journalId)
  }

  /** Drops a deleted journal's rows, and its photos that haven't gone up yet. */
  function forget(journalId: string) {
    for (const waiting of queue.filter(({ row }) => row.journalId === journalId)) {
      queue.splice(queue.indexOf(waiting), 1)
    }
    rows.value = rows.value.filter((row) => row.journalId !== journalId)
  }

  return { rows: shown, batch, add, clear, forget }
})
