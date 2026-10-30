import { computed, inject, type ComputedRef, type InjectionKey } from 'vue'

import type { BlockKind, JobStatus, PageStatus, UploadStatus } from './types'

// Every word the library says on its own. Screens pass their own copy as props; these are only
// the defaults and the bits nobody passes (close buttons, status names, screen reader labels).
export interface UiMessages {
  close: string
  dismiss: string
  menu: string
  mainNav: string
  breadcrumb: string
  notifications: string
  showDetails: string
  hideDetails: string
  showMore: string
  tryAgain: string
  clearSearch: string
  optional: string
  stillWriting: string
  stop: string
  send: string
  undo: string
  save: string
  looksRight: string
  changedNotSaved: string
  openPage: string
  pageWaiting: string
  pageReading: string
  pageUnreadable: string
  dropToAdd: string
  show: (label: string) => string
  hide: (label: string) => string
  page: (n: number) => string
  block: (seq: number, kind: string) => string
  progress: (value: number, max: number) => string
  sending: (fileName: string) => string
  score: (label: string) => string
  files: (n: number) => string
  scores: { words: string; meaning: string; blended: string }
  flags: { unsure: string; duplicate: string; edited: string; saved: string }
  pageStatus: Record<PageStatus, string>
  jobStatus: Record<JobStatus, string>
  uploadStatus: Record<UploadStatus, string>
  blockKind: Record<BlockKind, string>
}

/** Some messages to change; groups like `pageStatus` can be changed one entry at a time. */
export type UiMessagesOverride = {
  [K in keyof UiMessages]?: UiMessages[K] extends (...args: never[]) => string
    ? UiMessages[K]
    : UiMessages[K] extends object
      ? Partial<UiMessages[K]>
      : UiMessages[K]
}

const pageStatus: Record<PageStatus, string> = {
  uploaded: 'Uploaded',
  transcribing: 'Transcribing',
  indexing: 'Indexing',
  ready: 'Ready',
  failed: 'Failed',
}

const jobStatus: Record<JobStatus, string> = {
  queued: 'Waiting',
  running: 'Working',
  succeeded: 'Done',
  failed: 'Failed',
}

export const englishMessages: UiMessages = {
  close: 'Close',
  dismiss: 'Dismiss',
  menu: 'Menu',
  mainNav: 'Main',
  breadcrumb: 'Breadcrumb',
  notifications: 'Notifications',
  showDetails: 'Show details',
  hideDetails: 'Hide details',
  showMore: 'Show more',
  tryAgain: 'Try again',
  clearSearch: 'Clear search',
  optional: '(optional)',
  stillWriting: 'Still writing',
  stop: 'Stop',
  send: 'Send',
  undo: 'Undo',
  save: 'Save',
  looksRight: 'Looks right',
  changedNotSaved: 'changed, not saved',
  openPage: 'Open the page',
  pageWaiting: 'waiting…',
  pageReading: 'reading…',
  pageUnreadable: 'couldn’t read this one',
  dropToAdd: 'Let go to tuck them in',
  show: (label) => `Show ${label}`,
  hide: (label) => `Hide ${label}`,
  page: (n) => `Page ${n}`,
  block: (seq, kind) => `Block ${seq}, ${kind}`,
  progress: (value, max) => `${value} of ${max}`,
  sending: (fileName) => `Sending ${fileName}`,
  score: (label) => `${label} score`,
  files: (n) => (n === 1 ? '1 file' : `${n} files`),
  scores: { words: 'Words', meaning: 'Meaning', blended: 'Blended' },
  flags: {
    unsure: 'not quite sure',
    duplicate: 'already here',
    edited: 'edited by you',
    saved: 'saved',
  },
  pageStatus,
  jobStatus,
  // An upload follows its page's job, so it borrows their words, plus a few of its own.
  uploadStatus: {
    sending: 'Sending',
    queued: jobStatus.queued,
    transcribing: pageStatus.transcribing,
    indexing: pageStatus.indexing,
    ready: pageStatus.ready,
    duplicate: 'Already here',
    failed: pageStatus.failed,
    deleted: 'Deleted',
  },
  blockKind: {
    heading: 'Heading',
    paragraph: 'Paragraph',
    list: 'List',
    marginNote: 'Margin note',
    drawing: 'Drawing',
    other: 'Other',
  },
}

export function mergeMessages(base: UiMessages, override: UiMessagesOverride = {}): UiMessages {
  const merged: Record<string, unknown> = { ...base }
  for (const [key, value] of Object.entries(override)) {
    if (value === undefined) continue
    const current = merged[key]
    merged[key] =
      typeof value === 'object' && typeof current === 'object' ? { ...current, ...value } : value
  }
  return merged as unknown as UiMessages
}

export const messagesKey: InjectionKey<ComputedRef<UiMessages>> = Symbol('cottage messages')

const english = computed(() => englishMessages)

/** The library's words, from `createCottage({ messages })`, or English without it. */
export function useUiMessages(): ComputedRef<UiMessages> {
  return inject(messagesKey, english)
}
