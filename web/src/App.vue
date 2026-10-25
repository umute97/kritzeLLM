<script setup lang="ts">
import { KDoodle, KEmptyState, KLogo } from '@/ui'
</script>

<template>
  <main class="mx-auto flex min-h-screen max-w-xl flex-col items-center justify-center gap-6 p-6">
    <KLogo :size="44" />
    <KEmptyState
      title="The cottage is being furnished"
      text="Uploading and browsing pages arrive next. Until then, the API lives at /api/v1/docs."
    >
      <template #illustration><KDoodle name="daisy" /></template>
    </KEmptyState>
  </main>
</template>
