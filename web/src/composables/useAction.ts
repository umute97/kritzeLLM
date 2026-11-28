import { reactive, ref } from 'vue'

import { toastError, type ToastErrorOptions } from '@/utils/notify'

/** The toast for a failed call, worked out when it fails, so it speaks the language of then. */
export type Failure<Args extends unknown[]> = (
  ...args: Args
) => { title: string } & ToastErrorOptions

/** Runs an API call with a `busy` flag, and toasts when it fails. */
export function useAction<Args extends unknown[]>(
  action: (...args: Args) => Promise<unknown>,
  failure: Failure<Args>,
) {
  const busy = ref(false)

  async function run(...args: Args) {
    busy.value = true
    try {
      await action(...args)
    } catch (cause) {
      const { title, ...options } = failure(...args)
      toastError(cause, title, options)
    } finally {
      busy.value = false
    }
  }

  return reactive({ busy, run })
}
