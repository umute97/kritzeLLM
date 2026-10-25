import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { api, call } from '@/api/client'
import { ApiError } from '@/api/errors'
import { useAuth } from '@/stores/auth'
import { useHealth } from '@/stores/health'
import { json } from '@/test-utils'

beforeEach(() => {
  setActivePinia(createPinia())
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('call', () => {
  it('sends the token and hands back the data', async () => {
    const fetch = vi.fn<(request: Request) => Promise<Response>>(async () =>
      json({ items: [], nextCursor: null }),
    )
    vi.stubGlobal('fetch', fetch)
    useAuth().setToken('t0ken', false)

    const list = await call(api.GET('/journals'))

    expect(list).toEqual({ items: [], nextCursor: null })
    const request = fetch.mock.calls[0]![0]
    expect(request.headers.get('Authorization')).toBe('Bearer t0ken')
  })

  it('throws the server’s problem', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => json({ title: 'Not found', status: 404, detail: 'No such journal.' }, 404)),
    )
    const error = await call(
      api.GET('/journals/{journalId}', { params: { path: { journalId: 'jrn_x' } } }),
    ).catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(404)
    expect((error as ApiError).message).toBe('No such journal.')
  })

  it('asks for the token again on a 401', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => json({ title: 'Unauthorized', status: 401 }, 401)),
    )
    const auth = useAuth()
    auth.setToken('old', false)
    auth.accept()

    await expect(call(api.GET('/journals'))).rejects.toBeInstanceOf(ApiError)

    expect(auth.state).toBe('needed')
    expect(auth.rejected).toBe(true)
  })

  it('marks the API offline when nothing answers', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => Promise.reject(new TypeError('Failed to fetch'))),
    )

    const error = await call(api.GET('/journals')).catch((e: unknown) => e)

    expect((error as ApiError).offline).toBe(true)
    expect(useHealth().offline).toBe(true)
  })
})

describe('useAuth', () => {
  it('keeps a remembered token on this device and a plain one for the tab', () => {
    const auth = useAuth()
    auth.setToken('kept', true)
    expect(localStorage.getItem('kritzellm.token')).toBe('kept')
    auth.setToken('tab-only', false)
    expect(localStorage.getItem('kritzellm.token')).toBeNull()
    expect(sessionStorage.getItem('kritzellm.token')).toBe('tab-only')
    sessionStorage.clear()
  })
})
