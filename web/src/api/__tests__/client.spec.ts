import { beforeEach, describe, expect, it, vi } from 'vitest'

import { api, call, configureApi, fetchAll } from '@/api/client'
import { ApiError, fieldError } from '@/api/errors'
import { json, problem } from '@/test-utils'

const onUnauthorized = vi.fn()
const onOffline = vi.fn()

beforeEach(() => {
  onUnauthorized.mockReset()
  onOffline.mockReset()
  configureApi({ token: () => 't0ken', onUnauthorized, onOffline })
})

describe('call', () => {
  it('sends the token and hands back the data', async () => {
    const fetch = vi.fn<(request: Request) => Promise<Response>>(async () =>
      json({ items: [], nextCursor: null }),
    )
    vi.stubGlobal('fetch', fetch)

    const list = await call(api.GET('/journals'))

    expect(list).toEqual({ items: [], nextCursor: null })
    const request = fetch.mock.calls[0]![0]
    expect(request.headers.get('Authorization')).toBe('Bearer t0ken')
  })

  it('throws the server’s problem', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => json(problem(404, 'Not found', 'No such journal.'), 404)),
    )
    const error = await call(
      api.GET('/journals/{journalId}', { params: { path: { journalId: 'jrn_x' } } }),
    ).catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(404)
    expect((error as ApiError).message).toBe('No such journal.')
  })

  it('says so when the token is turned down', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => json(problem(401, 'Unauthorized'), 401)),
    )

    await expect(call(api.GET('/journals'))).rejects.toBeInstanceOf(ApiError)
    expect(onUnauthorized).toHaveBeenCalledOnce()
  })

  it('reports the API offline when nothing answers', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => Promise.reject(new TypeError('Failed to fetch'))),
    )

    const error = await call(api.GET('/journals')).catch((e: unknown) => e)

    expect((error as ApiError).offline).toBe(true)
    expect(onOffline).toHaveBeenCalledOnce()
  })

  it('passes on a call that was called off, which says nothing about the API', async () => {
    const aborted = new DOMException('The operation was aborted.', 'AbortError')
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => Promise.reject(aborted)),
    )

    await expect(call(api.GET('/journals'))).rejects.toBe(aborted)
    expect(onOffline).not.toHaveBeenCalled()
  })
})

describe('fetchAll', () => {
  it('follows the cursor to the last batch', async () => {
    const batch = vi
      .fn()
      .mockResolvedValueOnce({ items: [1, 2], nextCursor: 'c1' })
      .mockResolvedValueOnce({ items: [3], nextCursor: null })

    expect(await fetchAll(batch)).toEqual([1, 2, 3])
    expect(batch.mock.calls).toEqual([[undefined], ['c1']])
  })
})

describe('fieldError', () => {
  it('finds what the server said about one field', () => {
    const refused = new ApiError({
      ...problem(422, 'Unprocessable'),
      errors: [{ pointer: '/name', detail: 'Too long.' }],
    })
    expect(fieldError(refused, '/name')).toBe('Too long.')
    expect(fieldError(refused, '/title')).toBeUndefined()
    expect(fieldError(new Error('boom'), '/name')).toBeUndefined()
  })
})
