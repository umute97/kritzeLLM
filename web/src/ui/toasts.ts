import { computed, reactive } from 'vue'

export type ToastTone = 'success' | 'info' | 'warning' | 'error' | 'loading'

export interface ToastOptions {
  tone: ToastTone
  title: string
  detail?: string
  /** Shown behind "Show details", e.g. the HTTP status of an API problem. */
  details?: string
  action?: { label: string; run: () => void }
  progress?: { value: number; max: number }
  /** Milliseconds until it leaves on its own; `null` stays until dismissed. */
  timeout?: number | null
}

export interface Toast extends ToastOptions {
  id: number
}

/** Happy toasts float away; warnings, errors and progress wait for you. */
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

/** Changes a toast in place, e.g. upload progress or a loading toast that finished. */
function update(id: number, patch: Partial<ToastOptions>) {
  const toast = state.items.find((t) => t.id === id)
  if (!toast) return
  Object.assign(toast, patch)
  if ('tone' in patch || 'timeout' in patch) {
    disarm(id)
    arm(toast)
  }
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
    update,
    dismiss,
    pause,
    resume,
    clear,
  }
}
