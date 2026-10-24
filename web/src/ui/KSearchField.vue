<script setup lang="ts">
import { useId, useTemplateRef } from 'vue'

import KIcon from './KIcon.vue'

// Round like the buttons. Enter searches; the trailing slot takes a submit button.
defineOptions({ inheritAttrs: false })

const model = defineModel<string>({ default: '' })

withDefaults(defineProps<{ label: string; placeholder?: string; size?: 'md' | 'lg' }>(), {
  placeholder: undefined,
  size: 'md',
})

const emit = defineEmits<{ search: [query: string] }>()

const id = useId()
const input = useTemplateRef('input')

function clear() {
  model.value = ''
  input.value?.focus()
}
</script>

<template>
  <div
    :class="[
      'flex items-center gap-1 rounded-full border-ink bg-paper pl-4 focus-within:ring-4 focus-within:ring-accent/55',
      size === 'lg'
        ? 'min-h-14 border-2 pl-5 shadow-[0_4px_0_rgb(61_43_34/0.15)]'
        : 'min-h-[46px] border-[1.5px]',
    ]"
  >
    <KIcon name="search" :size="size === 'lg' ? 22 : 18" class="text-ink" />
    <label :for="id" class="sr-only">{{ label }}</label>
    <input
      :id="id"
      ref="input"
      v-model="model"
      v-bind="$attrs"
      type="search"
      :placeholder="placeholder"
      :class="[
        'min-w-0 flex-1 bg-transparent px-2 text-ink placeholder:text-hint focus:outline-none [&::-webkit-search-cancel-button]:hidden',
        size === 'lg' ? 'h-13 text-lg' : 'h-11 text-base',
      ]"
      @keydown.enter.prevent="emit('search', model)"
    />
    <button
      v-if="model"
      type="button"
      aria-label="Clear search"
      class="flex size-11 shrink-0 cursor-pointer items-center justify-center rounded-full text-ink hover:bg-ink/5"
      @click="clear"
    >
      <KIcon name="close" :size="16" />
    </button>
    <div v-if="$slots.default" class="pr-1.5">
      <slot />
    </div>
  </div>
</template>
