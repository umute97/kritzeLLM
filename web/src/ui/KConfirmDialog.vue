<script setup lang="ts">
import { ref, watchEffect } from 'vue'

import KButton from './KButton.vue'
import KDialog from './KDialog.vue'
import { useUiMessages } from './messages'

// "Are you sure?" The safe choice has the focus, and nothing closes it while `loading`.
// It holds on to its words while it closes, even if what it asked about is already gone.
const open = defineModel<boolean>('open', { default: false })

const props = withDefaults(
  defineProps<{
    title: string
    description?: string
    confirmLabel: string
    cancelLabel?: string
    tone?: 'danger' | 'main'
    loading?: boolean
  }>(),
  { description: undefined, cancelLabel: undefined, tone: 'danger' },
)

const emit = defineEmits<{ confirm: [] }>()

const ui = useUiMessages()
const words = ref({ title: props.title, description: props.description })

watchEffect(() => {
  if (open.value) words.value = { title: props.title, description: props.description }
})
</script>

<template>
  <KDialog
    v-model:open="open"
    :title="words.title"
    :description="words.description"
    :dismissible="!loading"
  >
    <template #footer>
      <KButton variant="second" autofocus :disabled="loading" @click="open = false">
        {{ cancelLabel ?? ui.keepIt }}
      </KButton>
      <KButton :variant="tone" :loading="loading" @click="emit('confirm')">
        {{ confirmLabel }}
      </KButton>
    </template>
  </KDialog>
</template>
