<script setup lang="ts">
import { ref } from 'vue'

import { ApiError } from '@/api/errors'
import { verifySession } from '@/utils/session'
import { useAuth } from '@/stores/auth'
import { KButton, KCheckbox, KTextField } from '@/ui'

const auth = useAuth()

const MISFIT = 'That token didn’t fit the lock. Check API_TOKEN in your .env.'

const token = ref(auth.token ?? '')
const remember = ref(auth.remembered)
const busy = ref(false)
const error = ref<string | undefined>(auth.rejected ? MISFIT : undefined)

async function submit() {
  const value = token.value.trim()
  if (!value) {
    error.value = 'Paste the token first'
    return
  }
  busy.value = true
  error.value = undefined
  auth.setToken(value, remember.value)
  try {
    if (!(await verifySession())) error.value = MISFIT
  } catch (cause) {
    error.value =
      cause instanceof ApiError && cause.offline
        ? 'kritzeLLM can’t reach the API right now.'
        : 'Something went wrong. Try again in a moment.'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <main class="mx-auto flex max-w-[460px] flex-col px-4 py-16 sm:py-24">
    <form
      class="flex flex-col gap-3.5 rounded-card border-[1.5px] border-ink bg-cream p-7 shadow-[0_6px_0_rgb(61_43_34/0.12)]"
      novalidate
      @submit.prevent="submit"
    >
      <h1 class="m-0 text-[28px] leading-tight">Knock knock</h1>
      <p class="m-0 text-[15px] text-muted">
        Paste the API token from your <code class="font-mono text-sm">.env</code> file to open the
        cottage door.
      </p>
      <KTextField
        v-model="token"
        label="API token"
        type="password"
        revealable
        autocomplete="off"
        spellcheck="false"
        :error="error"
      />
      <KCheckbox v-model="remember" label="Remember this token on this device" />
      <KButton type="submit" class="self-start" :loading="busy">Come in</KButton>
    </form>
  </main>
</template>
