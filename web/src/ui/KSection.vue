<script setup lang="ts">
import { useId } from 'vue'

import KCard from './KCard.vue'

// A titled part of a page, labelled by its own heading.
withDefaults(
  defineProps<{
    title: string
    description?: string
    size?: 'md' | 'lg'
    framed?: boolean
    align?: 'center' | 'end' | 'baseline'
    headingLevel?: 2 | 3
  }>(),
  { description: undefined, size: 'md', align: 'center', headingLevel: 2 },
)

const titleId = useId()
</script>

<template>
  <component
    :is="framed ? KCard : 'section'"
    v-bind="framed ? { as: 'section' } : {}"
    :aria-labelledby="titleId"
    :class="['flex min-w-0 flex-col', size === 'md' ? 'gap-4' : 'gap-5']"
  >
    <div
      :class="[
        'flex flex-wrap justify-between gap-x-4 gap-y-2.5',
        { center: 'items-center', end: 'items-end', baseline: 'items-baseline' }[align],
      ]"
    >
      <div class="flex min-w-0 flex-col gap-1">
        <div class="flex flex-wrap items-center gap-2">
          <component
            :is="`h${headingLevel}`"
            :id="titleId"
            :class="['m-0', size === 'md' ? 'text-[22px]' : 'text-3xl']"
          >
            {{ title }}
          </component>
          <slot name="title-after" />
        </div>
        <p
          v-if="description"
          class="m-0 max-w-[65ch] font-hand text-[19px] whitespace-pre-line text-bark"
        >
          {{ description }}
        </p>
      </div>
      <div v-if="$slots.aside" class="flex flex-wrap items-center gap-2.5">
        <slot name="aside" />
      </div>
    </div>
    <slot />
  </component>
</template>
