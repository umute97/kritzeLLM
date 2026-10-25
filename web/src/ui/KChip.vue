<script setup lang="ts">
import { toneClasses } from './tones'
import type { Tone } from './types'

withDefaults(defineProps<{ tone?: Tone; dot?: boolean; size?: 'md' | 'sm' }>(), {
  tone: 'plain',
  dot: true,
  size: 'md',
})
</script>

<template>
  <span
    :class="[
      'inline-flex shrink-0 items-center gap-1.5 rounded-full border font-bold whitespace-nowrap',
      size === 'md' ? 'px-3 py-0.5 text-[13px]' : 'px-2.5 py-px text-xs',
      toneClasses[tone].chip,
    ]"
  >
    <span
      v-if="dot"
      aria-hidden="true"
      :class="['size-2 rounded-full border-[1.5px]', toneClasses[tone].dot]"
    />
    <slot />
  </span>
</template>
