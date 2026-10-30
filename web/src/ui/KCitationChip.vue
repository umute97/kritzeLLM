<script setup lang="ts">
// "p. 12" inside an answer. Selected when its source is the one shown in Sources.
defineProps<{ label: string; selected?: boolean; disabled?: boolean }>()
</script>

<template>
  <button
    type="button"
    :aria-pressed="!!selected"
    :disabled="disabled"
    :class="[
      'mx-0.5 rounded-lg px-2 align-[2px] font-sans text-[13px] leading-[22px] font-bold text-ink',
      disabled
        ? 'cursor-not-allowed border border-dashed border-edge bg-mute text-muted'
        : selected
          ? 'cursor-pointer border-[1.5px] border-ink bg-accent'
          : 'cursor-pointer border border-clay bg-clay-soft hover:border-ink hover:shadow-press-sm',
    ]"
  >
    {{ label }}
  </button>
</template>
