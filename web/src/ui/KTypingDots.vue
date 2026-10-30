<script setup lang="ts">
import { useUiMessages } from './messages'

defineProps<{ label?: string }>()

const ui = useUiMessages()
</script>

<template>
  <span
    role="status"
    :aria-label="label ?? ui.stillWriting"
    class="inline-flex gap-1.5 rounded-full border-[1.5px] border-line bg-paper px-4 py-3"
  >
    <span class="size-[9px] animate-bob rounded-full border-[1.5px] border-ink bg-orchid" />
    <span
      class="size-[9px] animate-bob rounded-full border-[1.5px] border-ink bg-lemon [animation-delay:150ms]"
    />
    <span
      class="size-[9px] animate-bob rounded-full border-[1.5px] border-ink bg-herb [animation-delay:300ms]"
    />
  </span>
</template>
