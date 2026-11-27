<script setup lang="ts">
import KCard from './KCard.vue'

// A little dashed note beside a screen, with a handwritten title.
defineProps<{ title: string }>()
</script>

<template>
  <KCard variant="dashed" padding="sm" class="flex flex-col gap-1.5">
    <span class="font-hand text-lg text-bark">{{ title }}</span>
    <p class="m-0 text-sm leading-relaxed"><slot /></p>
  </KCard>
</template>
