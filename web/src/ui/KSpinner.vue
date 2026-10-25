<script setup lang="ts">
// Daisy for whole-page waits, ring inside buttons and rows. With a `label` it announces itself.
withDefaults(defineProps<{ variant?: 'ring' | 'daisy'; size?: number; label?: string }>(), {
  variant: 'ring',
  size: 18,
  label: undefined,
})
</script>

<template>
  <span
    class="inline-flex shrink-0"
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
    <svg v-else :width="size" :height="size" viewBox="0 0 64 64" class="animate-daisy">
      <g stroke="#3d2b22" stroke-width="1.5" fill="#fffdf8">
        <ellipse cx="32" cy="14" rx="7" ry="12" />
        <ellipse cx="32" cy="50" rx="7" ry="12" />
        <ellipse cx="14" cy="32" rx="12" ry="7" />
        <ellipse cx="50" cy="32" rx="12" ry="7" />
        <ellipse cx="19" cy="19" rx="7" ry="11" transform="rotate(-45 19 19)" />
        <ellipse cx="45" cy="45" rx="7" ry="11" transform="rotate(-45 45 45)" />
        <ellipse cx="45" cy="19" rx="7" ry="11" transform="rotate(45 45 19)" />
        <ellipse cx="19" cy="45" rx="7" ry="11" transform="rotate(45 19 45)" />
      </g>
      <circle cx="32" cy="32" r="8" fill="#efc06e" stroke="#3d2b22" stroke-width="1.5" />
    </svg>
  </span>
</template>
