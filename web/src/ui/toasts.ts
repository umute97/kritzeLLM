import { computed, reactive } from 'vue'

import type { IconName } from './icons'

export type ToastTone = 'success' | 'info' | 'warning' | 'error'

export interface ToastOptions {
  tone: ToastTone
  title: string
  detail?: string
  /** Shown behind "Show details", e.g. the HTTP status of an API problem. */
  technical?: string
  icon?: IconName
  action?: { label: string; run: () => void }
  /** Milliseconds until it leaves on its own; `null` stays until dismissed. */
  timeout?: number | null
}

export interface Toast extends ToastOptions {
  id: number
}

/** Happy toasts float away; warnings and errors wait for you. */
export const AUTO_DISMISS_MS = 5000

const state = reactive({ items: [] as Toast[] })
const timers = new Map<number, ReturnType<typeof setTimeout>>()
let nextId = 1

function arm(toast: Toast) {
  const fallback = toast.tone === 'success' || toast.tone === 'info' ? AUTO_DISMISS_MS : null
  const ms = toast.timeout === undefined ? fallback : toast.timeout
  if (!ms) return
  timers.set(
    toast.id,
    setTimeout(() => dismiss(toast.id), ms),
  )
}

function disarm(id: number) {
  clearTimeout(timers.get(id))
  timers.delete(id)
}

function push(options: ToastOptions): number {
  const toast: Toast = { ...options, id: nextId++ }
  state.items.push(toast)
  arm(toast)
  return toast.id
}

function dismiss(id: number) {
  disarm(id)
  state.items = state.items.filter((t) => t.id !== id)
}

/** Hovering a toast holds it in place. */
function pause(id: number) {
  disarm(id)
}

function resume(id: number) {
  const toast = state.items.find((t) => t.id === id)
  if (toast && !timers.has(id)) arm(toast)
}

function clear() {
  for (const id of timers.keys()) disarm(id)
  state.items = []
}

export function useToasts() {
  return {
    items: computed(() => state.items),
    push,
    dismiss,
    pause,
    resume,
    clear,
  }
}
