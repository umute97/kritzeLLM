import { defineStore } from 'pinia'
import { ref } from 'vue'

const KEY = 'kritzellm.token'

function storage(kind: 'local' | 'session'): Storage | null {
  try {
    return kind === 'local' ? globalThis.localStorage : globalThis.sessionStorage
  } catch {
    // Private windows and blocked site data can throw on access.
    return null
  }
}

function read(): { token: string | null; remembered: boolean } {
  const local = storage('local')?.getItem(KEY)
  if (local) return { token: local, remembered: true }
  return { token: storage('session')?.getItem(KEY) ?? null, remembered: false }
}

/**
 * The API token. `checking` until the first call tells us whether one is needed; `needed` shows
 * the token prompt. A token is kept for the tab, or on this device when "remember" is ticked.
 */
export const useAuth = defineStore('auth', () => {
  const saved = read()
  const token = ref<string | null>(saved.token)
  const remembered = ref(saved.remembered)
  const state = ref<'checking' | 'ok' | 'needed'>('checking')
  /** The API turned the last token down (rather than none being set yet). */
  const rejected = ref(false)

  function setToken(value: string, remember: boolean) {
    token.value = value
    remembered.value = remember
    try {
      storage('local')?.removeItem(KEY)
      storage('session')?.removeItem(KEY)
      storage(remember ? 'local' : 'session')?.setItem(KEY, value)
    } catch {
      // Not saving it only means asking again next time.
    }
  }

  function reject() {
    rejected.value = token.value !== null
    state.value = 'needed'
  }

  function accept() {
    rejected.value = false
    state.value = 'ok'
  }

  return { token, remembered, state, rejected, setToken, reject, accept }
})
