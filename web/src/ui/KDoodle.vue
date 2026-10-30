<script setup lang="ts">
import type { DoodleName } from './types'

// Little hand-drawn decorations. Sprinkle lightly: one per empty state or dialog, never everywhere.
withDefaults(defineProps<{ name: DoodleName; size?: number }>(), { size: 56 })
</script>

<template>
  <svg v-if="name === 'daisy'" :width="size" :height="size" viewBox="0 0 64 64" aria-hidden="true">
    <g stroke-width="1.5" class="stroke-ink fill-paper">
      <ellipse cx="32" cy="14" rx="7" ry="12" />
      <ellipse cx="32" cy="50" rx="7" ry="12" />
      <ellipse cx="14" cy="32" rx="12" ry="7" />
      <ellipse cx="50" cy="32" rx="12" ry="7" />
      <ellipse cx="19" cy="19" rx="7" ry="11" transform="rotate(-45 19 19)" />
      <ellipse cx="45" cy="45" rx="7" ry="11" transform="rotate(-45 45 45)" />
      <ellipse cx="45" cy="19" rx="7" ry="11" transform="rotate(45 45 19)" />
      <ellipse cx="19" cy="45" rx="7" ry="11" transform="rotate(45 19 45)" />
    </g>
    <circle cx="32" cy="32" r="8" stroke-width="1.5" class="fill-lemon stroke-ink" />
  </svg>
  <svg
    v-else-if="name === 'sprig'"
    :width="size"
    :height="size"
    viewBox="0 0 64 64"
    fill="none"
    aria-hidden="true"
  >
    <path
      d="M10 54 C24 42 36 30 54 10"
      stroke-width="2"
      stroke-linecap="round"
      class="stroke-clay"
    />
    <path
      d="M22 44 C14 40 12 32 14 26 C22 30 24 38 22 44Z M34 32 C30 24 32 16 38 12 C42 20 40 28 34 32Z M30 38 C38 40 46 36 50 30 C42 28 34 32 30 38Z"
      stroke-width="1.5"
      class="fill-herb stroke-ink"
    />
  </svg>
  <svg
    v-else-if="name === 'heart'"
    :width="size"
    :height="size"
    viewBox="0 0 56 56"
    aria-hidden="true"
  >
    <path
      d="M28 48 C10 36 4 26 8 17 C12 9 22 9 28 18 C34 9 44 9 48 17 C52 26 46 36 28 48Z"
      stroke-width="1.5"
      class="fill-orchid stroke-ink"
    />
  </svg>
  <svg
    v-else-if="name === 'sparkle'"
    :width="size"
    :height="size"
    viewBox="0 0 64 64"
    fill="none"
    aria-hidden="true"
  >
    <path
      d="M32 6 L36 26 L56 32 L36 38 L32 58 L28 38 L8 32 L28 26 Z"
      stroke-width="1.5"
      stroke-linejoin="round"
      class="fill-lemon stroke-ink"
    />
  </svg>
  <svg
    v-else
    :width="size"
    :height="(size * 2) / 3"
    viewBox="0 0 72 48"
    fill="none"
    aria-hidden="true"
  >
    <path
      d="M4 40 C12 24 20 24 28 32 C36 40 44 40 52 24 C58 12 64 10 68 12"
      stroke-width="2"
      stroke-linecap="round"
      stroke-dasharray="2 6"
      class="stroke-clay"
    />
    <circle cx="68" cy="12" r="4" stroke-width="1.5" class="fill-orchid stroke-ink" />
  </svg>
</template>
