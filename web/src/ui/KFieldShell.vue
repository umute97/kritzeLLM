<script setup lang="ts">
import { computed, useId } from 'vue'

import { noteId } from './attrs'
import KFieldNote from './KFieldNote.vue'
import { useUiMessages } from './messages'

// A label above, help or an error below, never just a placeholder.
const props = defineProps<{
  id?: string
  label: string
  help?: string
  error?: string
  optional?: boolean
  labelHidden?: boolean
}>()

const autoId = useId()
const id = computed(() => props.id ?? autoId)
const describedby = computed(() => noteId(id.value, props))

const ui = useUiMessages()
</script>

<template>
  <div class="flex flex-col gap-1.5">
    <label :for="id" :class="labelHidden ? 'sr-only' : 'text-sm font-bold'">
      {{ label }}
      <span v-if="optional" class="font-normal text-muted">{{ ui.optional }}</span>
    </label>
    <slot :id="id" :describedby="describedby" :invalid="!!error" />
    <KFieldNote :id="id" :help="help" :error="error" />
  </div>
</template>
