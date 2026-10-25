<script setup lang="ts" generic="T extends string">
import type { Option } from './types'

// A small pill switch between a few views, e.g. Photo / Text / Both.
const model = defineModel<T>({ required: true })

withDefaults(defineProps<{ label: string; options: Option<T>[]; size?: 'md' | 'sm' }>(), {
  size: 'md',
})
</script>

<template>
  <div
    role="group"
    :aria-label="label"
    class="inline-flex gap-1 self-start rounded-full border-[1.5px] border-ink bg-paper p-1"
  >
    <button
      v-for="option in options"
      :key="option.value"
      type="button"
      :aria-pressed="option.value === model"
      :class="[
        'cursor-pointer rounded-full border-[1.5px] font-bold text-ink',
        size === 'md' ? 'min-h-10 px-4.5 text-sm' : 'min-h-9 px-3.5 text-[13px]',
        option.value === model ? 'border-ink bg-accent' : 'border-transparent hover:bg-cream',
      ]"
      @click="model = option.value"
    >
      {{ option.label }}
    </button>
  </div>
</template>
