<script setup lang="ts">
import type { Component } from 'vue'

import { usePolymorphic, type LinkTarget } from './polymorphic'
import KBlockKindTag from './KBlockKindTag.vue'
import KHighlight from './KHighlight.vue'
import KScoreBars from './KScoreBars.vue'
import type { BlockKind } from './types'
import { useUiMessages } from './messages'

// One hit: a little page thumbnail, where it's from, the quote with the match marked, and the
// scores when debugging.
const props = withDefaults(
  defineProps<{
    pageNumber: number
    journal: string
    date?: string
    kind: BlockKind
    before?: string
    hit: string
    after?: string
    imageUrl?: string
    scores?: { words: number; meaning: number; blended: number }
    to?: LinkTarget
    as?: string | Component
  }>(),
  {
    date: undefined,
    before: '',
    after: '',
    imageUrl: undefined,
    scores: undefined,
    to: undefined,
    as: undefined,
  },
)

const element = usePolymorphic(() => ({ as: props.as, to: props.to }), 'a')

const ui = useUiMessages()
</script>

<template>
  <component
    :is="element.is"
    v-bind="element.attrs"
    class="flex gap-4.5 rounded-card border-[1.5px] border-ink bg-cream p-4 text-ink no-underline hover:bg-paper hover:text-ink"
  >
    <span
      aria-hidden="true"
      class="h-35 w-28 shrink-0 overflow-hidden rounded border border-line max-sm:hidden"
    >
      <img v-if="imageUrl" :src="imageUrl" alt="" loading="lazy" class="size-full object-cover" />
      <span
        v-else
        class="paper-lines block size-full p-2.5 font-hand text-sm leading-5 [--line:20px]"
      >
        <KHighlight :before="before" :hit="hit" :after="after" />
      </span>
    </span>
    <span class="flex min-w-0 flex-1 flex-col gap-2">
      <span class="flex flex-wrap items-center gap-x-3 gap-y-1.5">
        <strong class="font-display-soft text-xl">{{ ui.page(pageNumber) }}</strong>
        <span class="text-sm text-muted"
          >{{ journal }}<template v-if="date"> · {{ date }}</template></span
        >
        <KBlockKindTag :kind="kind" />
      </span>
      <span class="leading-relaxed"><KHighlight :before="before" :hit="hit" :after="after" /></span>
      <KScoreBars v-if="scores" class="mt-1" v-bind="scores" />
    </span>
  </component>
</template>
