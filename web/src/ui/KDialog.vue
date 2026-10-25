<script setup lang="ts">
import { useId, useTemplateRef, watch } from 'vue'

import KIconButton from './KIconButton.vue'

// Only for asking first, or a tiny form. Escape, the close button and the backdrop close it.
// Put `autofocus` on the safe choice in confirm dialogs.
const open = defineModel<boolean>('open', { default: false })

withDefaults(defineProps<{ title: string; description?: string; width?: 'sm' | 'md' }>(), {
  description: undefined,
  width: 'sm',
})

const dialog = useTemplateRef('dialog')
const titleId = useId()
const descriptionId = useId()

watch(
  [open, dialog],
  ([isOpen, el]) => {
    if (!el) return
    if (isOpen && !el.open) el.showModal()
    if (!isOpen && el.open) el.close()
  },
  { immediate: true },
)

function onBackdrop(event: MouseEvent) {
  if (event.target === dialog.value) open.value = false
}
</script>

<template>
  <dialog
    ref="dialog"
    :aria-labelledby="titleId"
    :aria-describedby="description ? descriptionId : undefined"
    :class="[
      'm-auto w-[calc(100%-2rem)] overflow-visible rounded-card border-[1.5px] border-ink bg-cream p-7 text-ink shadow-pop backdrop:bg-ink/50',
      width === 'sm' ? 'max-w-[420px]' : 'max-w-[460px]',
    ]"
    @close="open = false"
    @click="onBackdrop"
  >
    <div class="relative flex flex-col gap-3">
      <slot name="decoration" />
      <div class="flex items-start justify-between gap-3">
        <h2 :id="titleId" class="m-0 text-[26px] leading-tight">{{ title }}</h2>
        <KIconButton
          icon="close"
          label="Close"
          variant="plain"
          size="sm"
          class="-mt-1 -mr-2.5"
          @click="open = false"
        />
      </div>
      <p v-if="description" :id="descriptionId" class="m-0">{{ description }}</p>
      <slot />
      <div v-if="$slots.footer" class="mt-2 flex flex-wrap justify-end gap-2.5">
        <slot name="footer" />
      </div>
    </div>
  </dialog>
</template>
