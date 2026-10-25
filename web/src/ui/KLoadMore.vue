<script setup lang="ts">
import KButton from './KButton.vue'

// "Showing 8 of 48 pages" and a button for the next batch.
withDefaults(
  defineProps<{ summary: string; hasMore: boolean; loading?: boolean; label?: string }>(),
  { label: 'Show more' },
)

const emit = defineEmits<{ more: [] }>()
</script>

<template>
  <div class="flex flex-col items-center gap-2.5 pt-2">
    <span class="text-sm text-muted" aria-live="polite">{{ summary }}</span>
    <KButton v-if="hasMore" variant="second" :loading="loading" @click="emit('more')">
      {{ label }}
    </KButton>
  </div>
</template>
