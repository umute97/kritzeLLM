<script setup lang="ts">
import { computed, ref } from 'vue'

import { useSplitAttrs } from './attrs'
import KButton from './KButton.vue'
import KIcon from './KIcon.vue'
import { useUiMessages } from './messages'

// Drop files here or choose them. The caller checks the files and sets `error` to reject.
defineOptions({ inheritAttrs: false })

const props = withDefaults(
  defineProps<{
    title: string
    hint: string
    chooseLabel: string
    /** What a drag holds, e.g. "2 photos". */
    countLabel?: (count: number) => string
    accept?: string
    multiple?: boolean
    disabled?: boolean
    /** Shown instead of the title, e.g. "notes.pdf isn't a photo". */
    error?: string
    errorHint?: string
    headingLevel?: 2 | 3
  }>(),
  {
    countLabel: undefined,
    accept: 'image/jpeg,image/png,image/heic,image/heif,image/webp,.heic,.heif',
    multiple: true,
    error: undefined,
    errorHint: undefined,
    headingLevel: 2,
  },
)

const { rootAttrs, controlAttrs } = useSplitAttrs()
const ui = useUiMessages()

const emit = defineEmits<{ files: [files: File[]] }>()

const depth = ref(0)
const count = ref(0)
const dragging = computed(() => depth.value > 0 && !props.disabled)

function onEnter(event: DragEvent) {
  depth.value++
  count.value = event.dataTransfer?.items.length ?? 0
}

function onLeave() {
  depth.value = Math.max(0, depth.value - 1)
}

function onDrop(event: DragEvent) {
  depth.value = 0
  if (props.disabled) return
  const files = Array.from(event.dataTransfer?.files ?? [])
  if (files.length) emit('files', files)
}

function onPick(event: Event) {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files ?? [])
  input.value = ''
  if (files.length) emit('files', files)
}
</script>

<template>
  <div
    v-bind="rootAttrs()"
    :class="[
      'flex flex-col items-center justify-center gap-2 rounded-card px-6 py-9 text-center transition-[transform,background-color]',
      dragging
        ? 'scale-[1.01] border-[2.5px] border-ink bg-accent/45'
        : error
          ? 'border-2 border-dashed border-bark bg-bark-soft'
          : 'border-2 border-dashed border-clay bg-cream',
    ]"
    @dragenter.prevent="onEnter"
    @dragover.prevent
    @dragleave="onLeave"
    @drop.prevent="onDrop"
  >
    <slot name="illustration">
      <KIcon
        :name="dragging ? 'drop' : error ? 'file-x' : 'upload'"
        :size="28"
        :class="error && !dragging ? 'text-bark' : 'text-ink'"
      />
    </slot>
    <component :is="`h${headingLevel}`" class="m-0 text-[26px] leading-tight" aria-live="polite">
      {{ dragging ? ui.dropToAdd : (error ?? title) }}
    </component>
    <p v-if="dragging" class="m-0 font-hand text-xl">
      {{ (countLabel ?? ui.files)(count) }}
    </p>
    <p v-else class="m-0 max-w-[340px] text-sm" :class="error ? 'text-ink' : 'text-muted'">
      {{ error ? errorHint : hint }}
    </p>
    <KButton as="label" icon="upload" class="relative mt-1.5" :disabled="disabled">
      {{ chooseLabel }}
      <input
        v-bind="controlAttrs()"
        type="file"
        class="sr-only"
        :accept="accept"
        :multiple="multiple"
        :disabled="disabled"
        @change="onPick"
      />
    </KButton>
  </div>
</template>
