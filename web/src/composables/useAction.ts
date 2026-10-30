import { reactive, ref } from 'vue'

import { toastError, type ToastErrorOptions } from '@/utils/notify'

/** Runs an API call with a `busy` flag, and toasts when it fails. */
export function useAction<Args extends unknown[]>(
  action: (...args: Args) => Promise<unknown>,
  error: { title: string | ((...args: Args) => string) } & ToastErrorOptions,
) {
  const busy = ref(false)

  async function run(...args: Args) {
    busy.value = true
    try {
      await action(...args)
    } catch (cause) {
      const title = typeof error.title === 'function' ? error.title(...args) : error.title
      toastError(cause, title, error)
    } finally {
      busy.value = false
    }
  }

  return reactive({ busy, run })
}
