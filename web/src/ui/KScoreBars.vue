<script setup lang="ts">
import { computed } from 'vue'

// Why a search result came up: word match, closeness of meaning, and the blend that orders them.
const props = defineProps<{ words: number; meaning: number; blended: number }>()

const bars = computed(() => [
  { label: 'Words', value: props.words, color: 'bg-lemon' },
  { label: 'Meaning', value: props.meaning, color: 'bg-orchid' },
  { label: 'Blended', value: props.blended, color: 'bg-accent' },
])
</script>

<template>
  <div class="grid grid-cols-3 gap-3">
    <div v-for="bar in bars" :key="bar.label" class="flex flex-col gap-1">
      <div class="flex justify-between gap-1.5 text-xs">
        <span class="font-bold">{{ bar.label }}</span>
        <span class="font-mono">{{ bar.value.toFixed(2) }}</span>
      </div>
      <span
        role="meter"
        :aria-label="`${bar.label} score`"
        :aria-valuenow="bar.value"
        aria-valuemin="0"
        aria-valuemax="1"
        class="block h-2 overflow-hidden rounded-full border border-ink bg-paper"
      >
        <span
          :class="['block h-full', bar.color]"
          :style="{ width: `${Math.round(Math.min(1, Math.max(0, bar.value)) * 100)}%` }"
        />
      </span>
    </div>
  </div>
</template>
