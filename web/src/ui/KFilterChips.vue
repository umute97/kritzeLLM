<script setup lang="ts" generic="T extends string">
import KIcon from './KIcon.vue'
import type { Option } from './types'

// Picked chips get a tick, not just colour.
const model = defineModel<T>({ required: true })

defineProps<{ label: string; options: Option<T>[] }>()
</script>

<template>
  <div role="group" :aria-label="label" class="flex flex-wrap gap-2">
    <button
      v-for="option in options"
      :key="option.value"
      type="button"
      :aria-pressed="option.value === model"
      :class="[
        'inline-flex min-h-10 cursor-pointer items-center gap-1.5 rounded-full border-[1.5px] border-ink px-4 text-sm font-bold text-ink',
        option.value === model ? 'bg-accent' : 'bg-paper hover:bg-cream',
      ]"
      @click="model = option.value"
    >
      <KIcon v-if="option.value === model" name="check" :size="14" />
      {{ option.label }}
    </button>
  </div>
</template>
