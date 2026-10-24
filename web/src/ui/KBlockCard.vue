<script setup lang="ts">
import { computed } from 'vue'

import KButton from './KButton.vue'
import KFlag from './KFlag.vue'
import { blockKindLabels, type BlockKind } from './types'

// One transcribed block, editable. Cmd/Ctrl+Enter saves, Escape undoes.
// `active` mirrors hover/focus so the page can point at the same block elsewhere.
const text = defineModel<string>({ required: true })

const props = defineProps<{
  seq: number
  kind: BlockKind
  uncertain?: boolean
  dirty?: boolean
  saving?: boolean
  saved?: boolean
  active?: boolean
}>()

const emit = defineEmits<{
  save: []
  undo: []
  confirm: []
  activate: []
  deactivate: []
}>()

const rows = computed(() => {
  const min = props.kind === 'paragraph' || props.kind === 'list' ? 2 : 1
  const lines = text.value
    .split('\n')
    .reduce((n, line) => n + Math.ceil((line.length || 1) / 70), 0)
  return Math.min(10, Math.max(min, lines))
})

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && (event.metaKey || event.ctrlKey) && props.dirty) {
    event.preventDefault()
    emit('save')
  } else if (event.key === 'Escape' && props.dirty) {
    event.preventDefault()
    emit('undo')
  }
}
</script>

<template>
  <div
    :class="[
      'flex flex-col gap-2 rounded-card border-[1.5px] px-4 pt-3.5 pb-4 transition-colors',
      active || dirty ? 'border-ink bg-accent/30' : 'border-line bg-cream',
    ]"
    @mouseenter="emit('activate')"
    @mouseleave="emit('deactivate')"
    @focusin="emit('activate')"
    @focusout="emit('deactivate')"
  >
    <div class="flex flex-wrap items-center gap-2.5">
      <span
        aria-hidden="true"
        :class="[
          'flex size-6 items-center justify-center rounded-full border-[1.5px] border-ink text-xs font-bold',
          active || dirty ? 'bg-accent' : 'bg-paper',
        ]"
        >{{ seq }}</span
      >
      <span class="text-sm font-bold">{{ blockKindLabels[kind] }}</span>
      <KFlag v-if="uncertain && !dirty" kind="unsure" />
      <span v-if="dirty" class="text-xs font-bold text-muted">changed, not saved</span>
      <KFlag v-else-if="saved" kind="saved" />
      <span class="flex-1" />
      <template v-if="dirty">
        <KButton variant="quiet" size="sm" :disabled="saving" @click="emit('undo')">Undo</KButton>
        <KButton size="sm" :loading="saving" @click="emit('save')">Save</KButton>
      </template>
      <KButton v-else-if="uncertain" variant="second" size="sm" @click="emit('confirm')">
        Looks right
      </KButton>
    </div>
    <textarea
      v-model="text"
      :rows="rows"
      :aria-label="`Block ${seq}, ${blockKindLabels[kind]}`"
      :class="[
        'w-full resize-y rounded-field bg-paper px-3 py-2.5 leading-normal text-ink focus:outline-none',
        kind === 'drawing' && 'italic',
        dirty
          ? 'border-2 border-ink ring-4 ring-accent/45'
          : uncertain
            ? 'border-[1.5px] border-dashed border-clay focus:border-ink'
            : 'border-[1.5px] border-edge focus:border-ink',
      ]"
      @keydown="onKeydown"
    />
  </div>
</template>
