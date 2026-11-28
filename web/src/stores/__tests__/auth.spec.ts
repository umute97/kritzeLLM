import { describe, expect, it } from 'vitest'

import { useAuth } from '@/stores/auth'

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

  it('asks again after a refusal, saying so only when there was a token', () => {
    const auth = useAuth()
    auth.reject()
    expect(auth.state).toBe('needed')
    expect(auth.rejected).toBe(false)
    auth.setToken('old', false)
    auth.reject()
    expect(auth.rejected).toBe(true)
    auth.accept()
    expect(auth).toMatchObject({ state: 'ok', rejected: false })
    sessionStorage.clear()
  })
})
