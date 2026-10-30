<script setup lang="ts">
import KIconButton from './KIconButton.vue'

// Two arrows and what they move through, e.g. "‹ 12 of 48 ›" between pages, or "Journals 1–4 ‹ ›"
// on the shelf (`textFirst`).
withDefaults(
  defineProps<{
    prevLabel: string
    nextLabel: string
    canPrev?: boolean
    canNext?: boolean
    textFirst?: boolean
    label?: string
  }>(),
  { label: undefined },
)

const emit = defineEmits<{ prev: []; next: [] }>()
</script>

<template>
  <div :role="label ? 'group' : undefined" :aria-label="label" class="flex items-center gap-2.5">
    <slot v-if="textFirst" />
    <KIconButton
      icon="chevron-left"
      :label="prevLabel"
      :disabled="!canPrev"
      @click="emit('prev')"
    />
    <slot v-if="!textFirst" />
    <KIconButton
      icon="chevron-right"
      :label="nextLabel"
      :disabled="!canNext"
      @click="emit('next')"
    />
  </div>
</template>
