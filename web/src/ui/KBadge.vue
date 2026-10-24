<script setup lang="ts">
defineProps<{ count: number; label?: string }>()
</script>

<template>
  <span
    :aria-label="label"
    class="inline-flex h-5 min-w-5 items-center justify-center rounded-full border-[1.5px] border-ink bg-orchid px-1.5 text-[11px] font-bold text-ink"
    >{{ count }}</span
  >
</template>
