<script setup lang="ts">
// "p. 12" inside an answer. Active when its source is the one shown in Sources.
defineProps<{ label: string; active?: boolean }>()
</script>

<template>
  <button
    type="button"
    :aria-pressed="!!active"
    :class="[
      'mx-0.5 cursor-pointer rounded-lg px-2 align-[2px] font-sans text-[13px] leading-[22px] font-bold text-ink',
      active
        ? 'border-[1.5px] border-ink bg-accent'
        : 'border border-clay bg-clay-soft hover:border-ink hover:shadow-press-sm',
    ]"
  >
    {{ label }}
  </button>
</template>
