<script setup lang="ts">
import { computed, type Component } from 'vue'

import KIcon from './KIcon.vue'
import type { IconName } from './icons'
import KSpinner from './KSpinner.vue'
import { usePolymorphic, type LinkTarget } from './polymorphic'
import { disabledClass } from './styles'

// One `main` button per view; everything beside it is `second` or `quiet`.
// `danger` belongs in confirm dialogs only.
const props = withDefaults(
  defineProps<{
    variant?: 'main' | 'second' | 'quiet' | 'danger'
    size?: 'md' | 'sm'
    loading?: boolean
    disabled?: boolean
    to?: LinkTarget
    /** Render as another element or component, e.g. `'label'` or `'a'`. */
    as?: string | Component
    type?: 'button' | 'submit' | 'reset'
    icon?: IconName
  }>(),
  { variant: 'main', size: 'md', to: undefined, as: undefined, type: 'button', icon: undefined },
)

const inactive = computed(() => props.disabled || props.loading)
const element = usePolymorphic(() => ({
  as: props.as,
  to: props.to,
  inactive: inactive.value,
  type: props.type,
}))

const variants = {
  main: 'border-[1.5px] border-ink bg-accent text-ink hover:-translate-y-0.5 hover:bg-accent-strong active:translate-y-[3px] active:shadow-none',
  second: 'border-[1.5px] border-ink bg-paper text-ink hover:bg-cream',
  quiet: 'text-bark underline underline-offset-4 hover:text-ink',
  danger:
    'border-[1.5px] border-ink bg-bark text-cream hover:-translate-y-0.5 active:translate-y-[3px] active:shadow-none',
}

const classes = computed(() => {
  const lifted = props.variant === 'main' || props.variant === 'danger'
  return [
    'inline-flex items-center justify-center gap-2 rounded-full font-bold no-underline transition-[transform,box-shadow,background-color] duration-100 select-none',
    props.size === 'md' ? 'min-h-11 px-5.5 text-[15px]' : 'min-h-9 px-3.5 text-[13px]',
    props.disabled
      ? disabledClass
      : [
          variants[props.variant],
          lifted &&
            (props.size === 'md'
              ? 'shadow-press hover:shadow-lift'
              : 'shadow-press-sm hover:shadow-press'),
          props.loading ? 'cursor-progress' : 'cursor-pointer',
        ],
  ]
})
</script>

<template>
  <component
    :is="element.is"
    v-bind="element.attrs"
    :aria-busy="loading ? 'true' : undefined"
    :class="classes"
  >
    <KSpinner v-if="loading" :size="size === 'md' ? 18 : 14" />
    <slot v-else name="icon"><KIcon v-if="icon" :name="icon" /></slot>
    <slot />
  </component>
</template>
