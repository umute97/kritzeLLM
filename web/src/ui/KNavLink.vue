<script setup lang="ts">
import type { Component } from 'vue'

import KBadge from './KBadge.vue'
import { usePolymorphic, type LinkTarget } from './polymorphic'

// The current room gets the accent pill.
const props = withDefaults(
  defineProps<{
    to?: LinkTarget
    as?: string | Component
    current?: boolean
    badge?: number
    badgeLabel?: string
  }>(),
  { to: undefined, as: undefined, badge: undefined, badgeLabel: undefined },
)

const element = usePolymorphic(() => ({ as: props.as, to: props.to }), 'a')
</script>

<template>
  <component
    :is="element.is"
    v-bind="element.attrs"
    :aria-current="current ? 'page' : undefined"
    :class="[
      'inline-flex min-h-10 items-center gap-1.5 rounded-full border-[1.5px] px-4 font-bold text-ink no-underline hover:text-ink',
      current ? 'border-ink bg-accent' : 'border-transparent hover:bg-paper',
    ]"
  >
    <slot />
    <KBadge v-if="badge" :count="badge" :label="badgeLabel" />
  </component>
</template>
