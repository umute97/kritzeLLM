<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { RouterLink, RouterView } from 'vue-router'

import TokenPrompt from '@/components/TokenPrompt.vue'
import { verifySession } from '@/utils/session'
import { useAuth } from '@/stores/auth'
import { useHealth } from '@/stores/health'
import { KBanner, KButton, KLogo, KNavLink, KPage, KSpinner, KToastStack, KTopNav } from '@/ui'

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
        <RouterLink to="/" aria-label="kritzeLLM, your journals" class="no-underline">
          <KLogo />
        </RouterLink>
      </template>
      <KNavLink to="/" current>Pages</KNavLink>
      <template #end><span class="font-hand text-xl text-bark">hi there</span></template>
    </KTopNav>

    <KPage v-if="health.offline || health.database !== 'ok'" as="div" bare class="pt-6">
      <KBanner :title="health.offline ? 'The cottage door is shut' : 'The database is napping'">
        <template v-if="health.offline">
          kritzeLLM can’t reach the API. Is
          <code>just up</code>
          running?
        </template>
        <template v-else
          >The API is up, but its database isn’t answering, so pages can’t load.</template
        >
        <template #aside>
          <KButton variant="second" :loading="health.checking" @click="health.check()">
            Knock again
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
      label="Opening the cottage door"
    />

    <KToastStack />
  </div>
</template>
