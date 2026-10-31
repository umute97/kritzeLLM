<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, RouterView } from 'vue-router'

import LanguageSwitch from '@/components/LanguageSwitch.vue'
import TokenPrompt from '@/components/TokenPrompt.vue'
import { verifySession } from '@/utils/session'
import { useAuth } from '@/stores/auth'
import { useHealth } from '@/stores/health'
import { KBanner, KButton, KLogo, KNavLink, KPage, KSpinner, KToastStack, KTopNav } from '@/ui'

const { t } = useI18n()
const auth = useAuth()
const health = useHealth()

async function start() {
  try {
    await verifySession()
  } catch {
    // Offline: the banner shows, and we try again once the API answers.
  }
}

onMounted(async () => {
  await health.check()
  await start()
})

watch(
  () => health.offline,
  (offline, wasOffline) => {
    if (!offline && wasOffline && auth.state === 'checking') void start()
  },
)
</script>

<template>
  <div class="min-h-screen">
    <KTopNav>
      <template #brand>
        <RouterLink to="/" :aria-label="t('app.home')" class="no-underline">
          <KLogo />
        </RouterLink>
      </template>
      <KNavLink to="/" current>{{ t('app.pages') }}</KNavLink>
      <template #end>
        <div class="flex items-center gap-4">
          <span class="font-hand text-xl text-bark">{{ t('app.greeting') }}</span>
          <LanguageSwitch />
        </div>
      </template>
    </KTopNav>

    <KPage v-if="health.offline || health.database !== 'ok'" as="div" bare class="pt-6">
      <KBanner :title="health.offline ? t('app.offlineTitle') : t('app.databaseTitle')">
        <i18n-t v-if="health.offline" keypath="app.offline">
          <template #command><code>just up</code></template>
        </i18n-t>
        <template v-else>{{ t('app.database') }}</template>
        <template #aside>
          <KButton variant="second" :loading="health.checking" @click="health.check()">
            {{ t('app.knockAgain') }}
          </KButton>
        </template>
      </KBanner>
    </KPage>

    <TokenPrompt v-if="auth.state === 'needed'" />
    <RouterView v-else-if="auth.state === 'ok'" />
    <KSpinner
      v-else-if="!health.offline"
      block
      variant="daisy"
      :size="56"
      :label="t('app.opening')"
    />

    <KToastStack />
  </div>
</template>
