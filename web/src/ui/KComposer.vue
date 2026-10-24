<script setup lang="ts">
import { computed, useId } from 'vue'

import KButton from './KButton.vue'
import KIconButton from './KIconButton.vue'

// The writing box. Enter sends, Shift+Enter adds a line; while an answer streams, send becomes stop.
const text = defineModel<string>({ default: '' })

const props = withDefaults(
  defineProps<{ label?: string; placeholder?: string; streaming?: boolean; disabled?: boolean }>(),
  { label: 'Ask your journal', placeholder: 'Ask your journal anything' },
)

const emit = defineEmits<{ send: [text: string]; stop: [] }>()

const id = useId()
const canSend = computed(() => !props.disabled && !props.streaming && text.value.trim() !== '')

function send() {
  if (canSend.value) emit('send', text.value.trim())
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
    event.preventDefault()
    send()
  }
}
</script>

<template>
  <form
    class="flex items-end gap-2.5 rounded-card border-[1.5px] border-ink bg-paper p-2 focus-within:ring-4 focus-within:ring-accent/45"
    @submit.prevent="send"
  >
    <label :for="id" class="sr-only">{{ label }}</label>
    <textarea
      :id="id"
      v-model="text"
      rows="2"
      :placeholder="placeholder"
      :disabled="disabled"
      class="min-w-0 flex-1 resize-none bg-transparent px-2.5 py-2 leading-normal text-ink placeholder:text-hint focus:outline-none"
      @keydown="onKeydown"
    />
    <KButton v-if="streaming" variant="second" class="min-h-[46px]" @click="emit('stop')">
      <template #icon><span aria-hidden="true" class="size-3 rounded-[3px] bg-ink" /></template>
      Stop
    </KButton>
    <KIconButton
      v-else
      icon="arrow-up"
      label="Send"
      :variant="canSend ? 'main' : 'second'"
      :disabled="!canSend"
      @click="send"
    />
  </form>
</template>
