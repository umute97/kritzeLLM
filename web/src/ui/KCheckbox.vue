<script setup lang="ts">
import { computed, useId } from 'vue'

import { joinIds, noteId, useSplitAttrs } from './attrs'
import KFieldNote from './KFieldNote.vue'

defineOptions({ inheritAttrs: false })

const model = defineModel<boolean>({ default: false })

const props = defineProps<{
  label?: string
  help?: string
  error?: string
  disabled?: boolean
  id?: string
}>()

const autoId = useId()
const fieldId = computed(() => props.id ?? autoId)
const { rootAttrs, controlAttrs } = useSplitAttrs()
</script>

<template>
  <div v-bind="rootAttrs()" class="flex flex-col gap-1">
    <label
      :class="[
        'inline-flex min-h-11 items-center gap-2.5 font-semibold',
        disabled ? 'cursor-not-allowed text-muted' : 'cursor-pointer',
      ]"
    >
      <input
        :id="fieldId"
        v-bind="controlAttrs()"
        v-model="model"
        type="checkbox"
        :disabled="disabled"
        :aria-invalid="error ? 'true' : undefined"
        :aria-describedby="joinIds(noteId(fieldId, props), $attrs['aria-describedby'])"
        class="m-0 size-5.5 cursor-[inherit] accent-bark"
      />
      <slot>{{ label }}</slot>
    </label>
    <KFieldNote :id="fieldId" :help="help" :error="error" />
  </div>
</template>
