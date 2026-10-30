<script setup lang="ts">
import type { Component } from 'vue'

import { pageWidth } from './styles'

// The column a screen lives in: `wide` for the app, `narrow` for a lone card or message.
// `bare` drops the space above and below, for strips between the nav and the screen.
withDefaults(
  defineProps<{
    as?: string | Component
    width?: 'wide' | 'narrow'
    gap?: 'md' | 'lg'
    bare?: boolean
  }>(),
  { as: 'main', width: 'wide', gap: 'md' },
)
</script>

<template>
  <component
    :is="as"
    :class="[
      'flex flex-col',
      width === 'wide' ? pageWidth : 'mx-auto w-full max-w-[480px] px-4',
      gap === 'md' ? 'gap-6' : 'gap-10',
      !bare && (width === 'wide' ? 'pt-10 pb-20' : 'py-16 sm:py-24'),
    ]"
  >
    <slot />
  </component>
</template>
