import { defineStore } from 'pinia'
import { ref } from 'vue'

import { API_BASE } from '@/api/client'
import type { Health } from '@/api/types'

const RETRY_MS = 10_000

/** Whether the API (and its database) answer. Offline, it knocks again every few seconds. */
export const useHealth = defineStore('health', () => {
  const offline = ref(false)
  const database = ref<Health['database']>('ok')
  const checking = ref(false)
  let retry: ReturnType<typeof setTimeout> | undefined

  async function check(): Promise<boolean> {
    clearTimeout(retry)
    checking.value = true
    try {
      // Plain fetch: /health needs no token, and a failure here mustn't loop back into markOffline.
      const response = await globalThis.fetch(`${API_BASE}/health`)
      if (!response.ok) throw new Error(`health answered ${response.status}`)
      const health = (await response.json()) as Health
      offline.value = false
      database.value = health.database
    } catch {
      offline.value = true
    } finally {
      checking.value = false
    }
    if (offline.value || database.value !== 'ok') retry = setTimeout(check, RETRY_MS)
    return !offline.value && database.value === 'ok'
  }

  function markOffline() {
    if (offline.value) return
    offline.value = true
    clearTimeout(retry)
    retry = setTimeout(check, RETRY_MS)
  }

  return { offline, database, checking, check, markOffline }
})
