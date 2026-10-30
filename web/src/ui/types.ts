import type { IconName } from './icons'

// The API's vocabulary, as far as the components need it. Structural, so the generated client
// types fit in without a mapping.
export type PageStatus = 'uploaded' | 'transcribing' | 'indexing' | 'ready' | 'failed'
export type JobStatus = 'queued' | 'running' | 'succeeded' | 'failed'
export type BlockKind = 'heading' | 'paragraph' | 'list' | 'marginNote' | 'drawing' | 'other'

/** Soft colour families for chips. Each pairs a pale ground with readable ink. */
export type Tone = 'plain' | 'lemon' | 'orchid' | 'herb' | 'bark'

/** Journal cover colours, straight from the palette. */
export type CoverColor = 'herb' | 'clay' | 'orchid' | 'lemon'

export type UploadStatus =
  'sending' | 'queued' | 'transcribing' | 'indexing' | 'ready' | 'duplicate' | 'failed' | 'deleted'

export type StatusKind = 'page' | 'job' | 'upload'

export interface Option<T extends string = string> {
  value: T
  label: string
}

export interface Crumb {
  label: string
  /** Passed to the link component as `to` (router) and `href` (plain links). */
  to?: string | Record<string, unknown>
}

export interface MenuItem {
  id: string
  label: string
  icon?: IconName
  /** Danger items sit alone at the bottom, under a line. */
  danger?: boolean
  disabled?: boolean
}

export const pageStatusLabels: Record<PageStatus, string> = {
  uploaded: 'Uploaded',
  transcribing: 'Transcribing',
  indexing: 'Indexing',
  ready: 'Ready',
  failed: 'Failed',
}

export const pageStatusTones: Record<PageStatus, Tone> = {
  uploaded: 'plain',
  transcribing: 'lemon',
  indexing: 'orchid',
  ready: 'herb',
  failed: 'bark',
}

export const jobStatusLabels: Record<JobStatus, string> = {
  queued: 'Waiting',
  running: 'Working',
  succeeded: 'Done',
  failed: 'Failed',
}

export const jobStatusTones: Record<JobStatus, Tone> = {
  queued: 'plain',
  running: 'lemon',
  succeeded: 'herb',
  failed: 'bark',
}

// An upload follows its page's job, so it borrows their words and colours, plus a few of its own.
export const uploadStatusLabels: Record<UploadStatus, string> = {
  sending: 'Sending',
  queued: jobStatusLabels.queued,
  transcribing: pageStatusLabels.transcribing,
  indexing: pageStatusLabels.indexing,
  ready: pageStatusLabels.ready,
  duplicate: 'Already here',
  failed: pageStatusLabels.failed,
  deleted: 'Deleted',
}

export const uploadStatusTones: Record<UploadStatus, Tone> = {
  sending: 'plain',
  queued: jobStatusTones.queued,
  transcribing: pageStatusTones.transcribing,
  indexing: pageStatusTones.indexing,
  ready: pageStatusTones.ready,
  duplicate: 'orchid',
  failed: pageStatusTones.failed,
  deleted: 'plain',
}

export const blockKindLabels: Record<BlockKind, string> = {
  heading: 'Heading',
  paragraph: 'Paragraph',
  list: 'List',
  marginNote: 'Margin note',
  drawing: 'Drawing',
  other: 'Other',
}

/** A gentle, repeating tilt for pinned page cards, by position in the grid. */
export function tiltFor(index: number): number {
  return [-1.5, 1, -0.5, 1.5][index % 4] ?? 0
}
