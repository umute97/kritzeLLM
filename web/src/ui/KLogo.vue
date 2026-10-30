<script setup lang="ts">
// A pencil drawing a squiggle: kritzeln is German for "to scribble".
withDefaults(defineProps<{ size?: number; wordmark?: boolean }>(), { size: 30, wordmark: true })
</script>

<template>
  <span class="inline-flex items-center gap-2 text-ink">
    <svg :width="size" :height="size" viewBox="0 0 44 44" fill="none" aria-hidden="true">
      <path
        d="M4 39 C7 34 10 41 13 36 S15 31 16 30"
        :stroke-width="size >= 40 ? 2 : 2.5"
        class="stroke-clay"
        stroke-linecap="round"
      />
      <g
        transform="translate(16 30) rotate(-45)"
        :stroke-width="size >= 40 ? 1.5 : 2"
        class="stroke-ink"
        stroke-linejoin="round"
      >
        <path d="M0 0 L8 -4.5 L8 4.5 Z" class="fill-sand" />
        <path d="M0 0 L3 -1.7 L3 1.7 Z" class="fill-ink" />
        <rect x="8" y="-4.5" width="15" height="9" class="fill-lemon" />
        <rect x="23" y="-4.5" width="3.5" height="9" class="fill-cream" />
        <rect x="26.5" y="-4.5" width="5" height="9" rx="2" class="fill-orchid" />
      </g>
    </svg>
    <span
      v-if="wordmark"
      class="font-display-soft"
      :style="{ fontSize: `${Math.round(size * 0.8)}px` }"
      >kritzeLLM</span
    >
  </span>
</template>
