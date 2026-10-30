<script setup lang="ts">
import { KButton, KDoodle, KEmptyState } from '@/ui'
</script>

<template>
  <main class="mx-auto max-w-[560px] px-4 py-20">
    <KEmptyState
      title="Nothing lives here"
      text="This address doesn’t lead anywhere in the cottage."
    >
      <template #illustration><KDoodle name="squiggle" /></template>
      <KButton to="/">Back to your journals</KButton>
    </KEmptyState>
  </main>
</template>
