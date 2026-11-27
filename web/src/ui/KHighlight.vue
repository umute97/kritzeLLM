<script setup lang="ts">
import { computed } from 'vue'

import type { Mark } from './types'

// Words with some stretches marked, e.g. what a search matched or a cited quote.
const props = withDefaults(defineProps<{ text: string; marks?: Mark[]; soft?: boolean }>(), {
  marks: () => [],
})

const parts = computed(() => {
  const parts: { text: string; marked: boolean }[] = []
  let at = 0
  for (const [start, end] of props.marks) {
    if (start > at) parts.push({ text: props.text.slice(at, start), marked: false })
    parts.push({ text: props.text.slice(start, end), marked: true })
    at = end
  }
  if (at < props.text.length) parts.push({ text: props.text.slice(at), marked: false })
  return parts
})
</script>

<template>
  <span
    ><template v-for="(part, index) in parts" :key="index"
      ><mark
        v-if="part.marked"
        :class="['rounded px-0.5 text-ink', soft ? 'bg-orchid-soft' : 'bg-accent/60']"
        >{{ part.text }}</mark
      ><template v-else>{{ part.text }}</template></template
    ></span
  >
</template>
