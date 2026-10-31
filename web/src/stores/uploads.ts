import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { ApiError } from '@/api/errors'
import { uploadPage } from '@/api/upload'
import { i18n } from '@/i18n'
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
export function rejectReason(
  file: File,
): { reason: 'type' | 'size'; label: string; note: string } | null {
  const { t } = i18n.global
  const looksLikePhoto = TYPES.has(file.type) || (file.type === '' && EXTENSIONS.test(file.name))
  if (!looksLikePhoto) {
    return { reason: 'type', label: t('uploads.notPhoto'), note: t('uploads.notPhotoNote') }
  }
  if (file.size > MAX_BYTES) {
    const note = t('uploads.tooBigNote', { size: fileSize(file.size) })
    return { reason: 'size', label: t('uploads.tooBig'), note }
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
  const { t } = i18n.global

  function statusOf(row: UploadRow): {
    status: UploadStatus
    note?: string
    statusLabel?: string
    progress?: number
  } {
    if (row.own) return row.own
    const page = row.pageId ? pages.byId.get(row.pageId) : undefined
    // Uploads put their page in the store, so it's only missing once it was deleted.
    if (!page) return { status: 'deleted', note: t('uploads.pageDeleted') }
    const n = page.pageNumber
    if (row.duplicate) return { status: 'duplicate', note: t('uploads.samePhoto', { n }) }
    switch (page.status) {
      case 'uploaded':
        return { status: 'queued', note: t('uploads.waiting', { n }) }
      case 'transcribing':
        return { status: 'transcribing', note: t('uploads.reading', { n }) }
      case 'indexing':
        return { status: 'indexing', note: t('uploads.indexing', { n }) }
      case 'ready':
        return { status: 'ready', note: t('uploads.page', { n }) }
      case 'failed':
        return {
          status: 'failed',
          note: page.error?.detail ?? page.error?.title ?? t('uploads.page', { n }),
        }
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
      if (!first) return null
      const tooBig = rejectReason(first)?.reason === 'size'
      return t(tooBig ? 'uploads.isTooBig' : 'uploads.isNotPhoto', { name: first.name })
    }
    for (const file of files.slice(0, MAX_FILES)) {
      const reason = rejectReason(file)
      const row: UploadRow = {
        key: nextKey++,
        fileName: file.name,
        journalId,
        own: reason
          ? { status: 'failed', statusLabel: reason.label, note: reason.note }
          : {
              status: 'sending',
              progress: 0,
              note: t('uploads.sent', { sent: '0 KB', total: fileSize(file.size) }),
            },
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
            note: t('uploads.sent', { sent: fileSize(sent), total: fileSize(total) }),
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
          statusLabel: problem?.status === 413 ? t('uploads.tooBig') : undefined,
          note: problem?.detail ?? problem?.title ?? t('uploads.notUp'),
        }
        if (error instanceof ApiError && (error.offline || error.status === 401)) {
          // Everything after it would fail the same way.
          for (const waiting of queue.splice(0)) {
            waiting.row.own = { status: 'failed', note: t('uploads.notUpRetry') }
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
        title: t('uploads.tuckedInTitle'),
        detail: t('uploads.tuckedIn', sent),
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
