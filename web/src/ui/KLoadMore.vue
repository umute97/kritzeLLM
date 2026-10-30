<script setup lang="ts">
import KButton from './KButton.vue'
import { useUiMessages } from './messages'

// "Showing 8 of 48 pages" and a button for the next batch.
defineProps<{ summary: string; hasMore: boolean; loading?: boolean; label?: string }>()

const emit = defineEmits<{ more: [] }>()

const ui = useUiMessages()
</script>

<template>
  <div class="flex flex-col items-center gap-2.5 pt-2">
    <span class="text-sm text-muted" aria-live="polite">{{ summary }}</span>
    <KButton v-if="hasMore" variant="second" :loading="loading" @click="emit('more')">
      {{ label ?? ui.showMore }}
    </KButton>
  </div>
</template>
