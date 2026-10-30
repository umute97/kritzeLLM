<script setup lang="ts">
import type { Component } from 'vue'

import KIcon from './KIcon.vue'
import { usePolymorphic, type LinkTarget } from './polymorphic'
import { coverShape, disabledClass } from './styles'

// A dashed "add one" tile that sits in a row of covers.
const props = withDefaults(
  defineProps<{ label: string; disabled?: boolean; to?: LinkTarget; as?: string | Component }>(),
  { to: undefined, as: undefined },
)

const element = usePolymorphic(() => ({ as: props.as, to: props.to, inactive: props.disabled }))
</script>

<template>
  <component
    :is="element.is"
    v-bind="element.attrs"
    :class="[
      'flex flex-col items-center justify-center gap-1.5 font-bold no-underline',
      coverShape,
      disabled
        ? disabledClass
        : 'cursor-pointer border-2 border-dashed border-clay bg-cream text-ink hover:bg-paper hover:text-ink',
    ]"
  >
    <KIcon name="plus" :size="22" />
    {{ label }}
  </component>
</template>
