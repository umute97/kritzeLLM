<script setup lang="ts">
import type { Component } from 'vue'

import KHighlight from './KHighlight.vue'
import KIcon from './KIcon.vue'

// A cited page in the Sources panel. The picked one lifts and its quote takes the accent.
withDefaults(
  defineProps<{
    title: string
    date?: string
    before?: string
    quote: string
    after?: string
    active?: boolean
    linkAs?: string | Component
    to?: string | Record<string, unknown>
    linkLabel?: string
  }>(),
  {
    date: undefined,
    before: '',
    after: '',
    linkAs: 'a',
    to: undefined,
    linkLabel: 'Open the page',
  },
)
</script>

<template>
  <div
    :class="[
      'flex flex-col gap-2.5 rounded-field bg-paper p-3',
      active ? 'border-2 border-ink shadow-[0_5px_0_rgb(61_43_34/0.25)]' : 'border border-line',
    ]"
  >
    <div class="flex items-baseline justify-between gap-2">
      <strong class="text-[15px]">{{ title }}</strong>
      <span v-if="date" class="text-[13px] text-muted">{{ date }}</span>
    </div>
    <p
      class="paper-lines m-0 rounded border border-sand px-3 py-2.5 font-hand text-[19px] leading-[26px] [--line:26px]"
    >
      <KHighlight :before="before" :hit="quote" :after="after" :soft="!active" />
    </p>
    <component
      :is="linkAs"
      v-if="to"
      :to="to"
      :href="typeof to === 'string' ? to : undefined"
      class="inline-flex items-center gap-1.5 self-start text-sm font-bold"
    >
      {{ linkLabel }}
      <KIcon name="chevron-right" :size="16" />
    </component>
  </div>
</template>
