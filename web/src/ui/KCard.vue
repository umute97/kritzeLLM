<script setup lang="ts">
import type { Component } from 'vue'

// The cream card everything sits on. Dashed is for "nothing here yet" and "add one".
withDefaults(
  defineProps<{
    as?: string | Component
    variant?: 'solid' | 'dashed'
    padding?: 'none' | 'sm' | 'md' | 'lg'
    raised?: boolean
  }>(),
  { as: 'div', variant: 'solid', padding: 'md' },
)

const paddings = { none: '', sm: 'p-4', md: 'px-5 py-5.5 sm:px-7', lg: 'p-7' }
</script>

<template>
  <component
    :is="as"
    :class="[
      'rounded-card border-[1.5px] bg-cream text-ink',
      variant === 'solid' ? 'border-ink' : 'border-dashed border-clay',
      paddings[padding],
      raised && 'shadow-soft',
    ]"
  >
    <slot />
  </component>
</template>
