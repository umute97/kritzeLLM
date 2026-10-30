<script setup lang="ts">
import { computed } from 'vue'

import { useUiMessages } from './messages'
import KProgressBar from './KProgressBar.vue'

// Why a search result came up: word match, closeness of meaning, and the blend that orders them.
const props = defineProps<{ words: number; meaning: number; blended: number }>()

const ui = useUiMessages()

const bars = computed(() => [
  { label: ui.value.scores.words, value: props.words, color: 'lemon' as const },
  { label: ui.value.scores.meaning, value: props.meaning, color: 'orchid' as const },
  { label: ui.value.scores.blended, value: props.blended, color: 'accent' as const },
])
</script>

<template>
  <div class="grid grid-cols-3 gap-3">
    <div v-for="bar in bars" :key="bar.label" class="flex flex-col gap-1">
      <div class="flex justify-between gap-1.5 text-xs">
        <span class="font-bold">{{ bar.label }}</span>
        <span class="font-mono">{{ bar.value.toFixed(2) }}</span>
      </div>
      <KProgressBar
        meter
        size="sm"
        :max="1"
        :value="bar.value"
        :color="bar.color"
        :label="ui.score(bar.label)"
      />
    </div>
  </div>
</template>
