<script setup lang="ts">
import { computed } from 'vue'

import type { IconName } from './icons'
import KIcon from './KIcon.vue'

// For trouble that sticks around until it's fixed: the API is down, the token was refused,
// a page couldn't be read, a form came back with errors.
const props = withDefaults(
  defineProps<{ tone?: 'error' | 'warning' | 'info'; title: string; icon?: IconName }>(),
  { tone: 'error', icon: undefined },
)

const looks = {
  error: { icon: 'alert', badge: 'bg-bark text-cream', card: 'bg-bark-soft border-2 border-bark' },
  warning: {
    icon: 'key',
    badge: 'bg-lemon text-ink',
    card: 'bg-lemon-soft border-[1.5px] border-ink',
  },
  info: { icon: 'info', badge: 'bg-orchid text-ink', card: 'bg-paper border-[1.5px] border-ink' },
} as const

const look = computed(() => looks[props.tone])
</script>

<template>
  <div
    :role="tone === 'info' ? 'status' : 'alert'"
    :class="['flex flex-wrap items-start gap-3.5 rounded-card px-5 py-4.5', look.card]"
  >
    <span
      aria-hidden="true"
      :class="[
        'flex size-10 shrink-0 items-center justify-center rounded-full border-[1.5px] border-ink',
        look.badge,
      ]"
    >
      <KIcon :name="icon ?? look.icon" :size="20" />
    </span>
    <div class="flex min-w-0 flex-[1_1_300px] flex-col gap-1">
      <strong class="font-display text-xl font-semibold [font-variation-settings:'SOFT'_100]">{{
        title
      }}</strong>
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
