<script setup lang="ts">
import type { IconName } from './icons'
import KIcon from './KIcon.vue'

// A round badge holding an icon, or whatever the slot brings (a spinner, a number). Colour it
// with classes, e.g. `class="bg-lemon text-ink"`.
withDefaults(defineProps<{ icon?: IconName; size?: 'xs' | 'sm' | 'md' | 'lg' }>(), {
  icon: undefined,
  size: 'md',
})

const sizes = {
  xs: { box: 'size-6 text-xs font-bold', icon: 12 },
  sm: { box: 'size-8', icon: 16 },
  md: { box: 'size-9', icon: 16 },
  lg: { box: 'size-10', icon: 20 },
}
</script>

<template>
  <span
    aria-hidden="true"
    :class="[
      'flex shrink-0 items-center justify-center rounded-full border-[1.5px] border-ink',
      sizes[size].box,
    ]"
  >
    <slot><KIcon v-if="icon" :name="icon" :size="sizes[size].icon" /></slot>
  </span>
</template>
