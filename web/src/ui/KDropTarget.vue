<script setup lang="ts">
import { computed, ref } from 'vue'

import KIcon from './KIcon.vue'
import { useUiMessages } from './messages'

// Lets files be dropped anywhere on its content. The overlay is only a hint: pair it with a
// KFileButton so there's a way in without dragging.
const props = withDefaults(
  defineProps<{
    countLabel?: (count: number) => string
    disabled?: boolean
  }>(),
  { countLabel: undefined },
)

const emit = defineEmits<{ files: [files: File[]] }>()

const ui = useUiMessages()

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
</script>

<template>
  <div
    class="relative"
    @dragenter.prevent="onEnter"
    @dragover.prevent
    @dragleave="onLeave"
    @drop.prevent="onDrop"
  >
    <slot />
    <div
      v-if="dragging"
      aria-hidden="true"
      class="pointer-events-none absolute -inset-3 z-30 rounded-card border-[2.5px] border-ink bg-accent/45"
    >
      <div class="sticky top-1/3 flex flex-col items-center gap-2 px-6 py-9 text-center">
        <KIcon name="drop" :size="28" class="text-ink" />
        <p class="m-0 font-display-soft text-[26px] leading-tight">{{ ui.dropToAdd }}</p>
        <p class="m-0 font-hand text-xl">{{ (countLabel ?? ui.files)(count) }}</p>
      </div>
    </div>
  </div>
</template>
