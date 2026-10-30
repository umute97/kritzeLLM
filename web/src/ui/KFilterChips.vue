<script setup lang="ts" generic="T extends string">
import KIcon from './KIcon.vue'
import { pillClass } from './styles'
import type { Option } from './types'

// Picked chips get a tick, not just colour.
const model = defineModel<T>({ required: true })

defineProps<{ label: string; options: Option<T>[]; disabled?: boolean }>()
</script>

<template>
  <div role="group" :aria-label="label" class="flex flex-wrap gap-2">
    <button
      v-for="option in options"
      :key="option.value"
      type="button"
      :aria-pressed="option.value === model"
      :disabled="disabled"
      :class="[
        pillClass({ on: option.value === model, framed: true, disabled }),
        'min-h-10 px-4 text-sm',
      ]"
      @click="model = option.value"
    >
      <KIcon v-if="option.value === model" name="check" :size="14" />
      {{ option.label }}
    </button>
  </div>
</template>
