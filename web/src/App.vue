<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { RouterLink, RouterView } from 'vue-router'

import TokenPrompt from '@/components/TokenPrompt.vue'
import { verifySession } from '@/lib/session'
import { useAuth } from '@/stores/auth'
import { useHealth } from '@/stores/health'
import { KBanner, KButton, KLogo, KNavLink, KSpinner, KToastStack, KTopNav } from '@/ui'

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
      <KNavLink :as="RouterLink" to="/" active>Pages</KNavLink>
      <template #end>hi there</template>
    </KTopNav>

    <div
      v-if="health.offline || health.database !== 'ok'"
      class="mx-auto max-w-[1200px] px-4 pt-6 sm:px-6"
    >
      <KBanner :title="health.offline ? 'The cottage door is shut' : 'The database is napping'">
        <template v-if="health.offline">
          kritzeLLM can’t reach the API. Is
          <code class="rounded-md border border-line bg-paper px-1.5 font-mono text-sm"
            >just up</code
          >
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
    </div>

    <TokenPrompt v-if="auth.state === 'needed'" />
    <RouterView v-else-if="auth.state === 'ok'" />
    <div v-else-if="!health.offline" class="flex justify-center py-24">
      <KSpinner variant="daisy" :size="56" label="Opening the cottage door" />
    </div>

    <KToastStack />
  </div>
</template>
