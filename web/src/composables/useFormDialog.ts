import { reactive, ref, watch, type Ref } from 'vue'

import { fieldError } from '@/api/errors'
import { toastError } from '@/utils/notify'

/**
 * A small form in a `KDialog`: `fill()` runs each time it opens, and `submit()` saves, then
 * closes it. When the server refuses the field at `pointer`, its word shows under that field;
 * anything else toasts, titled `failed()`.
 */
export function useFormDialog(
  open: Ref<boolean>,
  options: {
    pointer: string
    fill: () => void
    save: () => Promise<unknown>
    failed: () => string
  },
) {
  const busy = ref(false)
  const error = ref<string>()

  watch(open, (isOpen) => {
    if (!isOpen) return
    error.value = undefined
    options.fill()
  })

  async function submit() {
    busy.value = true
    try {
      await options.save()
      open.value = false
    } catch (cause) {
      const field = fieldError(cause, options.pointer)
      if (field) error.value = field
      else toastError(cause, options.failed())
    } finally {
      busy.value = false
    }
  }

  return reactive({ busy, error, submit })
}
