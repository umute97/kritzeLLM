import createClient, { type Middleware } from 'openapi-fetch'

import { ApiError, offlineProblem, toProblem } from './errors'
import type { paths } from './schema'

export const API_BASE = '/api/v1'

export interface ApiConfig {
  token: () => string | null
  onUnauthorized: () => void
  onOffline: () => void
}

let config: ApiConfig = { token: () => null, onUnauthorized: () => {}, onOffline: () => {} }

/** Hands the client its token, and who to tell when the API refuses it or doesn't answer. */
export function configureApi(next: ApiConfig) {
  config = next
}

export function authHeaders(): Record<string, string> {
  const token = config.token()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export function reportUnauthorized() {
  config.onUnauthorized()
}

export function reportOffline() {
  config.onOffline()
}

const tokenMiddleware: Middleware = {
  onRequest({ request }) {
    for (const [name, value] of Object.entries(authHeaders())) request.headers.set(name, value)
    return request
  },
  onResponse({ response }) {
    if (response.status === 401) reportUnauthorized()
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

export function isAbort(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError'
}

/**
 * Unwraps an openapi-fetch call: the data, or an `ApiError` with the server's problem.
 * A request that never gets an answer reports the API offline, unless it was called off.
 */
export async function call<T>(request: Promise<FetchResult<T>>): Promise<T> {
  let result: FetchResult<T>
  try {
    result = await request
  } catch (cause) {
    if (isAbort(cause)) throw cause
    reportOffline()
    throw new ApiError(offlineProblem, { cause })
  }
  if (result.error !== undefined || !result.response.ok) {
    throw new ApiError(toProblem(result.error, result.response))
  }
  return result.data as T
}

/** Every item of a listing that pages with a cursor, one batch after another. */
export async function fetchAll<T>(
  batch: (cursor?: string) => Promise<{ items: T[]; nextCursor: string | null }>,
): Promise<T[]> {
  const all: T[] = []
  let cursor: string | undefined
  do {
    const list = await batch(cursor)
    all.push(...list.items)
    cursor = list.nextCursor ?? undefined
  } while (cursor)
  return all
}
