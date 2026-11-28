import type { IconName } from './icons'

// The API's vocabulary, as far as the components need it. Structural, so the generated client
// types fit in without a mapping.
export type PageStatus = 'uploaded' | 'transcribing' | 'indexing' | 'ready' | 'failed'
export type BlockKind = 'heading' | 'paragraph' | 'list' | 'marginNote' | 'drawing' | 'other'

/** Soft colour families for chips. Each pairs a pale ground with readable ink. */
export type Tone = 'plain' | 'lemon' | 'orchid' | 'herb' | 'bark'

export type DoodleName = 'daisy' | 'sprig' | 'heart' | 'sparkle' | 'squiggle'

/** Journal cover colours, straight from the palette. */
export type CoverColor = 'herb' | 'clay' | 'orchid' | 'lemon'

export type UploadStatus =
  'sending' | 'queued' | 'transcribing' | 'indexing' | 'ready' | 'duplicate' | 'failed' | 'deleted'

export type StatusKind = 'page' | 'upload'

/** A stretch of text to mark, from `start` up to (not including) `end`, as `String.slice` counts. */
export type Mark = [start: number, end: number]

/** A block's words in a search result, with what matched marked. */
export interface Quote {
  kind: BlockKind
  text: string
  /** Sorted, and not overlapping. */
  marks?: Mark[]
}

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
  /** Why it's disabled, shown under the label. */
  hint?: string
  run?: () => void
}

export const pageStatusTones: Record<PageStatus, Tone> = {
  uploaded: 'plain',
  transcribing: 'lemon',
  indexing: 'orchid',
  ready: 'herb',
  failed: 'bark',
}

// An upload follows its page, so it borrows the page's colours, plus a few of its own.
export const uploadStatusTones: Record<UploadStatus, Tone> = {
  sending: 'plain',
  queued: 'plain',
  transcribing: pageStatusTones.transcribing,
  indexing: pageStatusTones.indexing,
  ready: pageStatusTones.ready,
  duplicate: 'orchid',
  failed: pageStatusTones.failed,
  deleted: 'plain',
}

/** A gentle, repeating tilt for pinned page cards, by position in the grid. */
export function tiltFor(index: number): number {
  return [-1.5, 1, -0.5, 1.5][index % 4] ?? 0
}
