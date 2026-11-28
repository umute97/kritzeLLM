import { computed, reactive, ref, shallowRef } from 'vue'

import { ApiError } from '@/api/errors'

import { useAction, type Failure } from './useAction'

/**
 * The state behind a `KConfirmDialog`: `ask(subject)` opens it about something, `run()` does
 * `action` once confirmed. It closes when that worked, or when the error was one of `byStatus`;
 * on a real error it toasts and stays open for another go.
 */
export function useConfirm<T = void>(
  action: (about: T) => Promise<unknown>,
  failure: Failure<[T]>,
) {
  const open = ref(false)
  const subject = shallowRef<T>()

  const confirmed = useAction(async (about: T) => {
    try {
      await action(about)
    } catch (cause) {
      if (cause instanceof ApiError && failure(about).byStatus?.[cause.status]) open.value = false
      throw cause
    }
    open.value = false
  }, failure)

  function ask(about: T) {
    subject.value = about
    open.value = true
  }

  async function run() {
    if (!confirmed.busy) await confirmed.run(subject.value as T)
  }

  return reactive({ open, subject, busy: computed(() => confirmed.busy), ask, run })
}
