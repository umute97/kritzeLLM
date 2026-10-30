<script setup lang="ts">
import KIcon from './KIcon.vue'

// The line under a control: its error, or else its help. Point the control at it with `noteId()`.
defineProps<{ id: string; help?: string; error?: string }>()
</script>

<template>
  <p v-if="error" :id="`${id}-error`" class="flex items-center gap-1.5 text-sm font-bold text-bark">
    <KIcon name="alert-circle" :size="16" />
    {{ error }}
  </p>
  <p v-else-if="help" :id="`${id}-help`" class="text-[13px] text-muted">{{ help }}</p>
</template>
