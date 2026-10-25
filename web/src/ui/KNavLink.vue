<script setup lang="ts">
import type { Component } from 'vue'

import KBadge from './KBadge.vue'

// The current room gets the accent pill. Pass `as="RouterLink"`-style components with `to`.
withDefaults(
  defineProps<{ as?: string | Component; active?: boolean; badge?: number; badgeLabel?: string }>(),
  { as: 'a', badge: undefined, badgeLabel: undefined },
)
</script>

<template>
  <component
    :is="as"
    :aria-current="active ? 'page' : undefined"
    :class="[
      'inline-flex min-h-10 items-center gap-1.5 rounded-full border-[1.5px] px-4 font-bold text-ink no-underline hover:text-ink',
      active ? 'border-ink bg-accent' : 'border-transparent hover:bg-paper',
    ]"
  >
    <slot />
    <KBadge v-if="badge" :count="badge" :label="badgeLabel" />
  </component>
</template>
