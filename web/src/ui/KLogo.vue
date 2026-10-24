<script setup lang="ts">
// A pencil drawing a squiggle: kritzeln is German for "to scribble".
withDefaults(defineProps<{ size?: number; wordmark?: boolean }>(), { size: 30, wordmark: true })
</script>

<template>
  <span class="inline-flex items-center gap-2 text-ink">
    <svg :width="size" :height="size" viewBox="0 0 44 44" fill="none" aria-hidden="true">
      <path
        d="M4 39 C7 34 10 41 13 36 S15 31 16 30"
        stroke="#b46a55"
        :stroke-width="size >= 40 ? 2 : 2.5"
        stroke-linecap="round"
      />
      <g
        transform="translate(16 30) rotate(-45)"
        stroke="#3d2b22"
        :stroke-width="size >= 40 ? 1.5 : 2"
        stroke-linejoin="round"
      >
        <path d="M0 0 L8 -4.5 L8 4.5 Z" fill="#ede5d2" />
        <path d="M0 0 L3 -1.7 L3 1.7 Z" fill="#3d2b22" />
        <rect x="8" y="-4.5" width="15" height="9" fill="#efc06e" />
        <rect x="23" y="-4.5" width="3.5" height="9" fill="#fbf7ee" />
        <rect x="26.5" y="-4.5" width="5" height="9" rx="2" fill="#d6938a" />
      </g>
    </svg>
    <span
      v-if="wordmark"
      class="font-display font-semibold [font-variation-settings:'SOFT'_100]"
      :style="{ fontSize: `${Math.round(size * 0.8)}px` }"
      >kritzeLLM</span
    >
  </span>
</template>
