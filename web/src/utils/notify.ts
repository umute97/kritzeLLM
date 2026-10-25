import { ApiError } from '@/api/errors'
import { useToasts } from '@/ui'

/**
 * An error toast for a failed call. API problems show their own detail, with the status behind
 * "Show details". Offline and 401 are left out: the offline banner and the token prompt already
 * say so.
 */
export function toastError(error: unknown, title: string, retry?: () => void) {
  if (error instanceof ApiError && (error.offline || error.status === 401)) return
  const problem = error instanceof ApiError ? error.problem : undefined
  useToasts().push({
    tone: 'error',
    title,
    detail: problem?.detail ?? problem?.title ?? 'Something went wrong. Try again in a moment.',
    details: problem ? `${problem.status} ${problem.title}` : undefined,
    action: retry ? { label: 'Try again', run: retry } : undefined,
  })
}
