<script setup lang="ts">
import { KButton, KEmptyState } from '@/ui'

// Somewhere that isn't there (any more), with the way home.
defineProps<{ title: string; text: string }>()
</script>

<template>
  <KEmptyState :title="title" :text="text" doodle="squiggle">
    <KButton to="/">Back to your journals</KButton>
  </KEmptyState>
</template>
