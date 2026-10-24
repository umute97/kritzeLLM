<script setup lang="ts">
import KIcon from './KIcon.vue'

// A dashed "add one" tile that sits in a row of covers or cards.
defineProps<{ label: string }>()
</script>

<template>
  <button
    type="button"
    class="flex h-[132px] w-full cursor-pointer flex-col items-center justify-center gap-1.5 rounded-[9px_18px_18px_9px] border-2 border-dashed border-clay bg-cream font-bold text-ink hover:bg-paper"
  >
    <KIcon name="plus" :size="22" />
    {{ label }}
  </button>
</template>
