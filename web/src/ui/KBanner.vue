<script setup lang="ts">
import { computed } from 'vue'

import type { IconName } from './icons'
import KIconBadge from './KIconBadge.vue'
import { intentLooks } from './tones'

// For trouble that sticks around until it's fixed: the API is down, the token was refused,
// a page couldn't be read, a form came back with errors.
const props = withDefaults(
  defineProps<{ tone?: 'error' | 'warning' | 'info'; title: string; icon?: IconName }>(),
  { tone: 'error', icon: undefined },
)

const look = computed(() => intentLooks[props.tone])
</script>

<template>
  <div
    :role="tone === 'info' ? 'status' : 'alert'"
    :class="['flex flex-wrap items-start gap-3.5 rounded-card px-5 py-4.5', look.card]"
  >
    <KIconBadge :icon="icon ?? look.icon" size="lg" :class="look.badge" />
    <div class="flex min-w-0 flex-[1_1_300px] flex-col gap-1">
      <strong class="font-display-soft text-xl">{{ title }}</strong>
      <div class="text-[15px]"><slot /></div>
      <div v-if="$slots.actions" class="mt-2 flex flex-wrap gap-2.5">
        <slot name="actions" />
      </div>
    </div>
    <div v-if="$slots.aside" class="shrink-0">
      <slot name="aside" />
    </div>
  </div>
</template>
