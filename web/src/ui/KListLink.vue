<script setup lang="ts">
import type { Component } from 'vue'

import { usePolymorphic, type LinkTarget } from './polymorphic'

// One place in a list of them, e.g. an earlier chat: its name and a quiet line under it. The
// current one gets a frame.
const props = defineProps<{
  title: string
  meta?: string
  current?: boolean
  to?: LinkTarget
  as?: string | Component
}>()

const element = usePolymorphic(() => ({ as: props.as, to: props.to }), 'a')
</script>

<template>
  <component
    :is="element.is"
    v-bind="element.attrs"
    :aria-current="current ? 'page' : undefined"
    :class="[
      'flex flex-col gap-0.5 rounded-[14px] border-[1.5px] px-3 py-2.5 text-ink no-underline',
      current ? 'border-ink bg-paper' : 'border-transparent hover:bg-paper/60',
    ]"
  >
    <strong class="truncate text-[15px]">{{ title }}</strong>
    <span v-if="meta" class="text-[13px] text-muted">{{ meta }}</span>
  </component>
</template>
