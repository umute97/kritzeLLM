<script setup lang="ts">
import KIconButton from './KIconButton.vue'

// The API pages with a cursor and gives no total, so this shows the range and two arrows.
// The next arrow rests when there are no more.
defineProps<{ range: string; canBack: boolean; canNext: boolean; noun?: string }>()

const emit = defineEmits<{ back: []; next: [] }>()
</script>

<template>
  <div class="flex items-center gap-2.5">
    <span class="text-sm text-muted">{{ range }}</span>
    <KIconButton
      icon="chevron-left"
      :label="`Previous ${noun ?? 'items'}`"
      :disabled="!canBack"
      @click="emit('back')"
    />
    <KIconButton
      icon="chevron-right"
      :label="`More ${noun ?? 'items'}`"
      :disabled="!canNext"
      @click="emit('next')"
    />
  </div>
</template>
