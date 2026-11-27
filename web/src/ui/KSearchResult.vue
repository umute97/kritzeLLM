<script setup lang="ts">
import { computed, type Component } from 'vue'

import { usePolymorphic, type LinkTarget } from './polymorphic'
import KBlockKindTag from './KBlockKindTag.vue'
import KCard from './KCard.vue'
import KHighlight from './KHighlight.vue'
import KPhoto from './KPhoto.vue'
import type { Quote } from './types'
import { useUiMessages } from './messages'

// One hit: a little page thumbnail, where it's from, and the matching blocks with the match marked.
const props = withDefaults(
  defineProps<{
    pageNumber: number
    journal: string
    date?: string
    quotes: Quote[]
    /** Matching blocks left unquoted. */
    more?: number
    imageUrl?: string
    to?: LinkTarget
    as?: string | Component
  }>(),
  {
    date: undefined,
    more: 0,
    imageUrl: undefined,
    to: undefined,
    as: undefined,
  },
)

const element = usePolymorphic(() => ({ as: props.as, to: props.to }), 'a')
const kinds = computed(() => [...new Set(props.quotes.map((quote) => quote.kind))])

const ui = useUiMessages()
</script>

<template>
  <KCard
    :as="element.is"
    v-bind="element.attrs"
    padding="sm"
    class="flex gap-4.5 no-underline hover:bg-paper hover:text-ink"
  >
    <KPhoto
      :src="imageUrl"
      lazy
      aria-hidden="true"
      class="h-35 w-28 shrink-0 rounded border border-line [--line:20px] max-sm:hidden"
    >
      <span v-if="quotes[0]" class="block p-2.5 font-hand text-sm leading-5">
        <KHighlight :text="quotes[0].text" :marks="quotes[0].marks" />
      </span>
    </KPhoto>
    <span class="flex min-w-0 flex-1 flex-col gap-2">
      <span class="flex flex-wrap items-center gap-x-3 gap-y-1.5">
        <strong class="font-display-soft text-xl">{{ ui.page(pageNumber) }}</strong>
        <span class="text-sm text-muted"
          >{{ journal }}<template v-if="date"> · {{ date }}</template></span
        >
        <KBlockKindTag v-for="kind in kinds" :key="kind" :kind="kind" />
      </span>
      <span
        v-for="(quote, index) in quotes"
        :key="index"
        class="block leading-relaxed break-words whitespace-pre-line"
        ><KHighlight :text="quote.text" :marks="quote.marks"
      /></span>
      <span v-if="more" class="text-sm text-muted">{{ ui.moreBlocks(more) }}</span>
    </span>
  </KCard>
</template>
