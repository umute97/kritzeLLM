<script setup lang="ts">
import { computed, useId } from 'vue'

import { joinIds, noteId, useSplitAttrs } from './attrs'
import KFieldNote from './KFieldNote.vue'
import { disabledClass } from './styles'

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
const labelId = useId()
const { rootAttrs, controlAttrs } = useSplitAttrs()
</script>

<template>
  <div v-bind="rootAttrs()" class="flex flex-col gap-1">
    <div class="inline-flex min-h-11 items-center gap-2.5">
      <button
        :id="fieldId"
        v-bind="controlAttrs()"
        type="button"
        role="switch"
        :aria-checked="model"
        :aria-labelledby="labelId"
        :aria-invalid="error ? 'true' : undefined"
        :aria-describedby="joinIds(noteId(fieldId, props), $attrs['aria-describedby'])"
        :disabled="disabled"
        :class="[
          'relative h-8 w-14 shrink-0 rounded-full transition-colors',
          disabled
            ? disabledClass
            : ['cursor-pointer border-[1.5px] border-ink', model ? 'bg-accent' : 'bg-mute'],
        ]"
        @click="model = !model"
      >
        <span
          :class="[
            'absolute top-[3px] size-[23px] rounded-full border-[1.5px] border-ink bg-paper transition-[left] duration-150',
            model ? 'left-[27px]' : 'left-[3px]',
          ]"
        />
      </button>
      <span :id="labelId" class="font-semibold"
        ><slot>{{ label }}</slot></span
      >
    </div>
    <KFieldNote :id="fieldId" :help="help" :error="error" />
  </div>
</template>
