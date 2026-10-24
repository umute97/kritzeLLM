<script setup lang="ts">
import { blockKindLabels, type BlockKind } from './types'

defineProps<{ kind: BlockKind }>()

const marks: Record<BlockKind, string> = {
  heading: 'H',
  paragraph: '¶',
  list: '•',
  marginNote: '✎',
  drawing: '✿',
  other: '?',
}
</script>

<template>
  <span
    class="inline-flex items-center gap-1.5 rounded-md border border-edge bg-paper px-2.5 py-px text-[13px] font-bold"
  >
    <span aria-hidden="true" class="font-hand text-base leading-none text-bark">{{
      marks[kind]
    }}</span>
    {{ blockKindLabels[kind] }}
  </span>
</template>
