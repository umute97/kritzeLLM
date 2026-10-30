<script setup lang="ts">
import KCard from './KCard.vue'
import KDoodle from './KDoodle.vue'
import type { DoodleName } from './types'

// Say what's missing, then one way forward.
withDefaults(
  defineProps<{
    title: string
    text?: string
    framed?: boolean
    headingLevel?: 2 | 3
    doodle?: DoodleName
  }>(),
  { text: undefined, framed: true, headingLevel: 2, doodle: undefined },
)
</script>

<template>
  <component
    :is="framed ? KCard : 'div'"
    v-bind="framed ? { variant: 'dashed', padding: 'none' } : {}"
    class="flex flex-col items-center gap-2 px-5 py-7 text-center"
  >
    <slot name="illustration"><KDoodle v-if="doodle" :name="doodle" /></slot>
    <component :is="`h${headingLevel}`" class="m-0 text-[22px]">{{ title }}</component>
    <p v-if="text || $slots.text" class="m-0 max-w-[420px] text-sm text-muted">
      <slot name="text">{{ text }}</slot>
    </p>
    <div v-if="$slots.default" class="mt-1.5 flex flex-wrap justify-center gap-2">
      <slot />
    </div>
  </component>
</template>
