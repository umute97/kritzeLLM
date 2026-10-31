<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { ApiError } from '@/api/errors'
import { verifySession } from '@/utils/session'
import { useAuth } from '@/stores/auth'
import { KButton, KCard, KCheckbox, KPage, KTextField } from '@/ui'

const { t } = useI18n()
const auth = useAuth()

const token = ref(auth.token ?? '')
const remember = ref(auth.remembered)
const busy = ref(false)
const error = ref<string | undefined>(auth.rejected ? t('token.misfit') : undefined)

async function submit() {
  const value = token.value.trim()
  if (!value) {
    error.value = t('token.empty')
    return
  }
  busy.value = true
  error.value = undefined
  auth.setToken(value, remember.value)
  try {
    if (!(await verifySession())) error.value = t('token.misfit')
  } catch (cause) {
    error.value =
      cause instanceof ApiError && cause.offline ? t('token.offline') : t('errors.generic')
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <KPage width="narrow">
    <KCard
      as="form"
      padding="lg"
      raised
      class="flex flex-col gap-3.5"
      novalidate
      @submit.prevent="submit"
    >
      <h1 class="m-0 text-[28px] leading-tight">{{ t('token.title') }}</h1>
      <i18n-t keypath="token.intro" tag="p" class="m-0 text-[15px] text-muted">
        <template #file><code>.env</code></template>
      </i18n-t>
      <KTextField
        v-model="token"
        :label="t('token.label')"
        type="password"
        revealable
        autocomplete="off"
        spellcheck="false"
        :error="error"
      />
      <KCheckbox v-model="remember" :label="t('token.remember')" />
      <KButton type="submit" class="self-start" :loading="busy">{{ t('token.submit') }}</KButton>
    </KCard>
  </KPage>
</template>
