<script setup lang="ts">
import { computed } from 'vue'

import KJournalCover from './KJournalCover.vue'
import KPageCard from './KPageCard.vue'
import KSkeleton from './KSkeleton.vue'
import { coverShape } from './styles'

// Journal covers or page cards, laid out like the shelf and the board. The default slot brings
// the `<li>`s. When `empty`, the `#empty` slot takes a row as tall as a real card would.
const props = withDefaults(
  defineProps<{
    kind: 'covers' | 'pages'
    loading?: boolean
    empty?: boolean
    skeletons?: number
  }>(),
  { skeletons: 4 },
)

const layout = computed(() =>
  props.kind === 'covers'
    ? { grid: 'grid-cols-2 gap-6 sm:grid-cols-4', skeleton: coverShape }
    : {
        grid: 'grid-cols-[repeat(auto-fill,minmax(190px,1fr))] gap-x-6 gap-y-8 pt-3',
        skeleton: 'h-[250px]',
      },
)
</script>

<template>
  <div v-if="empty && !loading" :class="['grid', layout.grid]">
    <!-- An invisible card shares the row, so the row is as tall as the cards it stands in for. -->
    <div aria-hidden="true" inert class="invisible col-start-1 row-start-1">
      <KJournalCover v-if="kind === 'covers'" as="div" name="Sizer" meta="Sizer" />
      <KPageCard v-else as="div" :page-number="1" status="ready" date="Sizer" />
    </div>
    <div class="col-span-full row-start-1 grid">
      <slot name="empty" />
    </div>
  </div>
  <ul
    v-else
    :class="['m-0 grid list-none p-0', layout.grid]"
    :aria-busy="loading ? 'true' : undefined"
  >
    <template v-if="loading">
      <li v-for="n in skeletons" :key="n">
        <KSkeleton shape="block" :class="layout.skeleton" />
      </li>
    </template>
    <slot v-else />
  </ul>
</template>
