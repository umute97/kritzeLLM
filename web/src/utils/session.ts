import { api, call } from '@/api/client'
import { ApiError } from '@/api/errors'
import { useAuth } from '@/stores/auth'

/**
 * Asks the API whether the current token (or none) is welcome. True when it is; false on a 401,
 * which also opens the token prompt. Other failures (offline) are thrown.
 */
export async function verifySession(): Promise<boolean> {
  try {
    await call(api.GET('/journals', { params: { query: { limit: 1 } } }))
    useAuth().accept()
    return true
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) return false
    throw error
  }
}
