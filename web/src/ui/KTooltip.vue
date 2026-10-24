<script setup lang="ts">
import { ref, useId } from 'vue'

// On hover and focus, for icon buttons. Short, no full stop, never the only place something
// is said. Bind the slot's `describedby` to the trigger.
defineProps<{ text: string }>()

const id = useId()
const shown = ref(false)
</script>

<template>
  <span
    class="relative inline-flex"
    @mouseenter="shown = true"
    @mouseleave="shown = false"
    @focusin="shown = true"
    @focusout="shown = false"
    @keydown.esc="shown = false"
  >
    <slot :describedby="id" />
    <span
      v-show="shown"
      :id="id"
      role="tooltip"
      class="pointer-events-none absolute bottom-full left-1/2 z-40 mb-2.5 -translate-x-1/2 rounded-lg bg-ink px-3 py-1.5 text-[13px] font-semibold whitespace-nowrap text-cream"
    >
      {{ text }}
      <span
        aria-hidden="true"
        class="absolute -bottom-1.5 left-1/2 -ml-1.5 size-2.5 rotate-45 bg-ink"
      />
    </span>
  </span>
</template>
