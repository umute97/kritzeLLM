<script setup lang="ts">
import { computed, type Component } from 'vue'

import type { IconName } from './icons'
import KIcon from './KIcon.vue'
import { usePolymorphic } from './polymorphic'

// Icon-only buttons always carry a label for screen readers.
const props = withDefaults(
  defineProps<{
    icon: IconName
    label: string
    variant?: 'second' | 'main' | 'plain'
    size?: 'md' | 'sm'
    pressed?: boolean
    disabled?: boolean
    as?: string | Component
    type?: 'button' | 'submit' | 'reset'
  }>(),
  { variant: 'second', size: 'md', pressed: undefined, as: 'button', type: 'button' },
)

const element = usePolymorphic(
  () => props.as,
  () => props.disabled,
  () => props.type,
)

const classes = computed(() => [
  'inline-flex shrink-0 items-center justify-center rounded-full text-ink',
  props.size === 'md' ? 'size-11' : 'size-9',
  props.disabled
    ? 'cursor-not-allowed border-[1.5px] border-dashed border-edge bg-mute text-muted'
    : [
        'cursor-pointer',
        props.variant === 'plain' && 'hover:bg-ink/5',
        props.variant === 'second' &&
          (props.pressed
            ? 'border-[1.5px] border-ink bg-accent'
            : 'border-[1.5px] border-ink bg-paper hover:bg-cream'),
        props.variant === 'main' &&
          'border-[1.5px] border-ink bg-accent shadow-press hover:bg-accent-strong',
      ],
])
</script>

<template>
  <component :is="as" v-bind="element" :aria-label="label" :aria-pressed="pressed" :class="classes">
    <KIcon :name="icon" :size="size === 'md' ? 18 : 16" />
  </component>
</template>
