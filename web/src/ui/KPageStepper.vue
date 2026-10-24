<script setup lang="ts">
import KIconButton from './KIconButton.vue'

// "‹ 12 of 48 ›" between neighbouring pages of a journal.
defineProps<{
  current: number
  total?: number
  prevLabel: string
  nextLabel: string
  canPrev?: boolean
  canNext?: boolean
}>()

const emit = defineEmits<{ prev: []; next: [] }>()
</script>

<template>
  <div class="flex items-center gap-2.5">
    <KIconButton
      icon="chevron-left"
      :label="prevLabel"
      :disabled="!canPrev"
      @click="emit('prev')"
    />
    <span class="font-bold">
      {{ current }}<span v-if="total" class="font-normal text-muted"> of {{ total }}</span>
    </span>
    <KIconButton
      icon="chevron-right"
      :label="nextLabel"
      :disabled="!canNext"
      @click="emit('next')"
    />
  </div>
</template>
