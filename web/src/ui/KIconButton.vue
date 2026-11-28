<script setup lang="ts">
import { computed, type Component } from 'vue'

import type { IconName } from './icons'
import KIcon from './KIcon.vue'
import { usePolymorphic, type LinkTarget } from './polymorphic'
import { buttonLooks, disabledClass } from './styles'

// Icon-only buttons always carry a label for screen readers.
const props = withDefaults(
  defineProps<{
    icon: IconName
    label: string
    variant?: 'second' | 'main' | 'quiet'
    size?: 'md' | 'sm'
    pressed?: boolean
    disabled?: boolean
    to?: LinkTarget
    as?: string | Component
    type?: 'button' | 'submit' | 'reset'
  }>(),
  // Without the `undefined`, Vue would make a missing `pressed` false and say aria-pressed.
  { variant: 'second', size: 'md', pressed: undefined, type: 'button' },
)

const element = usePolymorphic(() => ({
  as: props.as,
  to: props.to,
  inactive: props.disabled,
  type: props.type,
}))

const classes = computed(() => [
  'inline-flex shrink-0 items-center justify-center rounded-full text-ink',
  props.size === 'md' ? 'size-11' : 'size-9',
  props.disabled
    ? disabledClass
    : [
        'cursor-pointer',
        props.variant === 'quiet' && 'hover:bg-ink/5',
        props.variant === 'second' &&
          (props.pressed ? 'border-[1.5px] border-ink bg-accent' : buttonLooks.second),
        props.variant === 'main' && [buttonLooks.main, 'shadow-press'],
      ],
])
</script>

<template>
  <component
    :is="element.is"
    v-bind="element.attrs"
    :aria-label="label"
    :aria-pressed="pressed"
    :class="classes"
  >
    <KIcon :name="icon" :size="size === 'md' ? 18 : 16" />
  </component>
</template>
