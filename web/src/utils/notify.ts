import { ApiError } from '@/api/errors'
import { useToasts, type ToastOptions } from '@/ui'

export interface ToastErrorOptions {
  retry?: () => void
  /** A friendlier toast for statuses that aren't really errors, e.g. a 409 while a page is busy. */
  byStatus?: Record<number, Partial<ToastOptions>>
}

/**
 * An error toast for a failed call. API problems show their own detail, with the status behind
 * "Show details". Offline and 401 are left out: the offline banner and the token prompt already
 * say so.
 */
export function toastError(error: unknown, title: string, options: ToastErrorOptions = {}) {
  if (error instanceof ApiError && (error.offline || error.status === 401)) return
  const special = error instanceof ApiError ? options.byStatus?.[error.status] : undefined
  if (special) {
    useToasts().push({ tone: 'info', title, ...special })
    return
  }
  const problem = error instanceof ApiError ? error.problem : undefined
  useToasts().push({
    tone: 'error',
    title,
    detail: problem?.detail ?? problem?.title ?? 'Something went wrong. Try again in a moment.',
    technical: problem ? `${problem.status} ${problem.title}` : undefined,
    action: options.retry ? { label: 'Try again', run: options.retry } : undefined,
  })
}
