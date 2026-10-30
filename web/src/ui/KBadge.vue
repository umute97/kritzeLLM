<script setup lang="ts">
// A plain span's aria-label isn't read out, so the label rides along as hidden text instead.
defineProps<{ count: number; label?: string }>()
</script>

<template>
  <span
    class="inline-flex h-5 min-w-5 items-center justify-center rounded-full border-[1.5px] border-ink bg-orchid px-1.5 text-[11px] font-bold text-ink"
    ><span :aria-hidden="label ? 'true' : undefined">{{ count }}</span
    ><span v-if="label" class="sr-only">{{ label }}</span></span
  >
</template>
