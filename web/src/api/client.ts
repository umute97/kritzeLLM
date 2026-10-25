import createClient, { type Middleware } from 'openapi-fetch'

import { useAuth } from '@/stores/auth'
import { useHealth } from '@/stores/health'

import { ApiError, offlineProblem, toProblem } from './errors'
import type { paths } from './schema'

export const API_BASE = '/api/v1'

/** Sends the token along, and asks for it again whenever the API turns it down. */
const tokenMiddleware: Middleware = {
  onRequest({ request }) {
    const { token } = useAuth()
    if (token) request.headers.set('Authorization', `Bearer ${token}`)
    return request
  },
  onResponse({ response }) {
    if (response.status === 401) useAuth().reject()
    return response
  },
}

export const api = createClient<paths>({
  // Absolute, because openapi-fetch builds `Request`s, which don't resolve relative URLs outside
  // a browser (tests).
  baseUrl: `${globalThis.location.origin}${API_BASE}`,
  // Looked up per call, so tests can swap `fetch` out.
  fetch: (request) => globalThis.fetch(request),
})
api.use(tokenMiddleware)

interface FetchResult<T> {
  data?: T
  error?: unknown
  response: Response
}

/**
 * Unwraps an openapi-fetch call: the data, or an `ApiError` with the server's problem.
 * A request that never gets an answer marks the API offline.
 */
export async function call<T>(request: Promise<FetchResult<T>>): Promise<T> {
  let result: FetchResult<T>
  try {
    result = await request
  } catch (cause) {
    useHealth().markOffline()
    throw new ApiError(offlineProblem, { cause })
  }
  if (result.error !== undefined || !result.response.ok) {
    throw new ApiError(toProblem(result.error, result.response))
  }
  return result.data as T
}
