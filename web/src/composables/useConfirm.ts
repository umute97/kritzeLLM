import { reactive, ref, shallowRef } from 'vue'

import { ApiError } from '@/api/errors'
import { toastError, type ToastErrorOptions } from '@/utils/notify'

/**
 * The state behind a `KConfirmDialog`: `ask(subject)` opens it about something, `run()` does the
 * thing once confirmed. It closes when that worked, or when the error was one of `byStatus`;
 * on a real error it toasts and stays open for another go.
 */
export function useConfirm<T = void>() {
  const open = ref(false)
  const subject = shallowRef<T>()
  const busy = ref(false)

  function ask(about: T) {
    subject.value = about
    open.value = true
  }

  async function run(
    action: (about: T) => Promise<unknown>,
    error: { title: string } & ToastErrorOptions,
  ) {
    if (busy.value) return
    busy.value = true
    try {
      await action(subject.value as T)
      open.value = false
    } catch (cause) {
      toastError(cause, error.title, error)
      if (cause instanceof ApiError && error.byStatus?.[cause.status]) open.value = false
    } finally {
      busy.value = false
    }
  }

  return reactive({ open, subject, busy, ask, run })
}
