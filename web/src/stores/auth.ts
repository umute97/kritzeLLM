import { defineStore } from 'pinia'
import { ref } from 'vue'

import { readStored, writeStored } from '@/utils/storage'

const KEY = 'kritzellm.token'

function read(): { token: string | null; remembered: boolean } {
  const local = readStored(KEY)
  if (local) return { token: local, remembered: true }
  return { token: readStored(KEY, 'session'), remembered: false }
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
    writeStored(KEY, remember ? value : null)
    writeStored(KEY, remember ? null : value, 'session')
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
