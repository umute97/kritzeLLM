<script setup lang="ts">
// Shaped like what's coming: size it with classes, e.g. `class="h-3 w-2/3"`.
withDefaults(defineProps<{ shape?: 'line' | 'block' }>(), { shape: 'line' })
</script>

<template>
  <span
    aria-hidden="true"
    :class="[
      'block animate-pulse-soft bg-mute',
      shape === 'line' ? 'rounded-full' : 'rounded-field',
    ]"
  />
</template>
