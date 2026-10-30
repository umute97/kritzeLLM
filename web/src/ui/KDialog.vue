<script setup lang="ts">
import { useId, useTemplateRef, watch } from 'vue'

import KIconButton from './KIconButton.vue'

// Only for asking first, or a tiny form. Escape, the close button and the backdrop close it,
// unless it isn't `dismissible` (e.g. while saving). Put `autofocus` on the safe choice in
// confirm dialogs. A `form` dialog wraps the body and the footer in one form, so a footer
// `type="submit"` button submits it and the dialog emits `submit`.
const open = defineModel<boolean>('open', { default: false })

const props = withDefaults(
  defineProps<{
    title: string
    description?: string
    width?: 'sm' | 'md'
    form?: boolean
    dismissible?: boolean
  }>(),
  { description: undefined, width: 'sm', dismissible: true },
)

const emit = defineEmits<{ submit: [] }>()

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

function dismiss() {
  if (props.dismissible) open.value = false
}

function onCancel(event: Event) {
  if (!props.dismissible) event.preventDefault()
}

// The card fills the dialog edge to edge, so only a backdrop click lands on the dialog itself.
function onBackdrop(event: MouseEvent) {
  if (event.target === dialog.value) dismiss()
}

function onSubmit(event: Event) {
  event.preventDefault()
  emit('submit')
}
</script>

<template>
  <dialog
    ref="dialog"
    :aria-labelledby="titleId"
    :aria-describedby="description ? descriptionId : undefined"
    :class="[
      'm-auto w-[calc(100%-2rem)] overflow-visible rounded-card border-[1.5px] border-ink bg-cream p-0 text-ink shadow-pop backdrop:bg-ink/50',
      width === 'sm' ? 'max-w-[420px]' : 'max-w-[460px]',
    ]"
    @cancel="onCancel"
    @close="open = false"
    @click="onBackdrop"
  >
    <component
      :is="form ? 'form' : 'div'"
      :novalidate="form || undefined"
      class="relative flex flex-col gap-3 p-7"
      v-on="form ? { submit: onSubmit } : {}"
    >
      <slot name="decoration" />
      <div class="flex items-start justify-between gap-3">
        <h2 :id="titleId" class="m-0 text-[26px] leading-tight">{{ title }}</h2>
        <KIconButton
          icon="close"
          label="Close"
          variant="plain"
          size="sm"
          :disabled="!dismissible"
          class="-mt-1 -mr-2.5"
          @click="dismiss"
        />
      </div>
      <p v-if="description" :id="descriptionId" class="m-0">{{ description }}</p>
      <slot />
      <div v-if="$slots.footer" class="mt-2 flex flex-wrap justify-end gap-2.5">
        <slot name="footer" />
      </div>
    </component>
  </dialog>
</template>
