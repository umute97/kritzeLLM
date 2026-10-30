<script setup lang="ts">
import type { Component } from 'vue'

import { usePolymorphic, type LinkTarget } from './polymorphic'
import { coverShape } from './styles'
import type { CoverColor } from './types'

// A notebook on the shelf. The open one lifts and gets a thicker line.
const props = withDefaults(
  defineProps<{
    name: string
    meta?: string
    color?: CoverColor
    selected?: boolean
    to?: LinkTarget
    as?: string | Component
  }>(),
  { meta: undefined, color: 'herb', to: undefined, as: undefined },
)

const element = usePolymorphic(() => ({ as: props.as, to: props.to }))

const covers: Record<CoverColor, string> = {
  herb: 'bg-herb text-ink',
  clay: 'bg-clay text-cream',
  orchid: 'bg-orchid text-ink',
  lemon: 'bg-lemon text-ink',
}
</script>

<template>
  <component
    :is="element.is"
    v-bind="element.attrs"
    :aria-pressed="element.is === 'button' ? selected : undefined"
    :aria-current="element.is !== 'button' && selected ? 'true' : undefined"
    :class="[
      'flex w-full cursor-pointer flex-col gap-2.5 bg-transparent p-0 text-left text-ink no-underline transition-transform hover:text-ink',
      selected ? '-translate-y-1' : 'hover:-translate-y-0.5',
    ]"
  >
    <span
      :class="[
        'relative block overflow-hidden border-ink',
        coverShape,
        covers[color],
        selected ? 'border-[2.5px] shadow-lift' : 'border-[1.5px] shadow-cover',
      ]"
    >
      <span aria-hidden="true" class="absolute inset-y-0 left-4 w-[3px] bg-ink/30" />
      <span
        aria-hidden="true"
        class="absolute -top-1 right-5.5 h-11 w-3.5 border-[1.5px] border-t-0 border-ink bg-accent"
      />
      <span class="absolute right-4 bottom-4 left-8.5 font-hand text-[26px] leading-[1.1]">{{
        name
      }}</span>
    </span>
    <span v-if="meta" class="text-sm text-muted">{{ meta }}</span>
  </component>
</template>
