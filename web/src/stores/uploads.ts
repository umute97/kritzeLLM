import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { ApiError } from '@/api/errors'
import type { Problem } from '@/api/types'
import { uploadPage } from '@/api/upload'
import { i18n } from '@/i18n'
import { looksLikePhoto, MAX_BYTES, MAX_FILES } from '@/utils/photos'
import { useToasts, type UploadStatus } from '@/ui'

import { useJournals } from './journals'
import { usePages } from './pages'

export type RejectReason = 'type' | 'size'

/** Why a file can't go up, or null when it can. */
export function rejectReason(file: File): RejectReason | null {
  if (!looksLikePhoto(file)) return 'type'
  return file.size > MAX_BYTES ? 'size' : null
}

/** How a row is doing. The batch strip puts it into words. */
export interface RowStatus {
  status: UploadStatus
  sent?: number
  total?: number
  pageNumber?: number
  /** Why it never went up: turned away here, or stopped because the ones before it failed. */
  reason?: RejectReason | 'stopped'
  /** The server's word on a failed upload, or on a page that couldn't be read. */
  problem?: Problem | null
}

export interface UploadRow {
  key: number
  fileName: string
  journalId: string
  /** Set while sending, or for rows that never got a page. */
  own?: RowStatus
  pageId?: string
  duplicate?: boolean
}

export type ShownRow = UploadRow & RowStatus

export interface Batch {
  rows: ShownRow[]
  counts: { done: number; skipped: number; failed: number; deleted: number; busy: number }
  active: boolean
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

  function statusOf(row: UploadRow): RowStatus {
    if (row.own) return row.own
    const page = row.pageId ? pages.byId.get(row.pageId) : undefined
    // Uploads put their page in the store, so it's only missing once it was deleted.
    if (!page) return { status: 'deleted' }
    const pageNumber = page.pageNumber
    if (row.duplicate) return { status: 'duplicate', pageNumber }
    if (page.status === 'failed') return { status: 'failed', pageNumber, problem: page.error }
    return { status: page.status === 'uploaded' ? 'queued' : page.status, pageNumber }
  }

  const shown = computed(() => rows.value.map((row) => ({ ...row, ...statusOf(row) })))

  function batch(journalId: string): Batch {
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

  /** Adds photos to a journal. When none of them can go up, hands back the first and why. */
  function add(journalId: string, files: File[]): { file: File; reason: RejectReason } | null {
    const checked = files.slice(0, MAX_FILES).map((file) => ({ file, reason: rejectReason(file) }))
    if (checked.every(({ reason }) => reason)) {
      const first = checked[0]
      return first?.reason ? { file: first.file, reason: first.reason } : null
    }
    for (const { file, reason } of checked) {
      rows.value.push({
        key: nextKey++,
        fileName: file.name,
        journalId,
        own: reason
          ? { status: 'failed', reason, total: file.size }
          : { status: 'sending', sent: 0, total: file.size },
      })
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
          row.own = { status: 'sending', sent, total }
        })
        const item = result.items[0]!
        row.pageId = item.page.id
        row.duplicate = item.duplicate
        row.own = undefined
        if (!item.duplicate) sent++
        pages.put(item.page)
      } catch (error) {
        row.own = { status: 'failed', problem: error instanceof ApiError ? error.problem : null }
        if (error instanceof ApiError && (error.offline || error.status === 401)) {
          // Everything after it would fail the same way.
          for (const waiting of queue.splice(0)) {
            waiting.row.own = { status: 'failed', reason: 'stopped' }
          }
        }
      }
    }
    running = false
    const journals = useJournals()
    for (const id of batchJournals) void journals.refresh(id).catch(() => {})
    if (sent > 0) {
      const { t } = i18n.global
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
