<script setup lang="ts">
// A quote with the matching words marked: `before`, the `hit`, then `after`.
withDefaults(defineProps<{ before?: string; hit: string; after?: string; soft?: boolean }>(), {
  before: '',
  after: '',
})
</script>

<template>
  <span
    >{{ before
    }}<mark :class="['rounded px-0.5 text-ink', soft ? 'bg-orchid-soft' : 'bg-accent/60']">{{
      hit
    }}</mark
    >{{ after }}</span
  >
</template>
