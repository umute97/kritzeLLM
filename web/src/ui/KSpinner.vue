<script setup lang="ts">
import KDoodle from './KDoodle.vue'

// Daisy for whole-page waits, ring inside buttons and rows. With a `label` it announces itself.
withDefaults(
  defineProps<{ variant?: 'ring' | 'daisy'; size?: number; label?: string; block?: boolean }>(),
  { variant: 'ring', size: 18, label: undefined },
)
</script>

<template>
  <span
    :class="block ? 'flex justify-center py-24' : 'inline-flex shrink-0'"
    :role="label ? 'status' : undefined"
    :aria-label="label"
    :aria-hidden="label ? undefined : 'true'"
  >
    <svg
      v-if="variant === 'ring'"
      :width="size"
      :height="size"
      viewBox="0 0 24 24"
      fill="none"
      class="animate-spin"
    >
      <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-opacity="0.25" stroke-width="3" />
      <path
        d="M21 12a9 9 0 0 0-9-9"
        stroke="currentColor"
        stroke-width="3"
        stroke-linecap="round"
      />
    </svg>
    <KDoodle v-else name="daisy" :size="size" class="animate-daisy" />
  </span>
</template>
