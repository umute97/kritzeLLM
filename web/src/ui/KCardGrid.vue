<script setup lang="ts">
import { computed } from 'vue'

import KSkeleton from './KSkeleton.vue'
import { coverShape } from './styles'

// Journal covers or page cards, laid out like the shelf and the board. The default slot brings
// the `<li>`s.
const props = withDefaults(
  defineProps<{ kind: 'covers' | 'pages'; loading?: boolean; skeletons?: number }>(),
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
  <ul :class="['m-0 grid list-none p-0', layout.grid]" :aria-busy="loading ? 'true' : undefined">
    <template v-if="loading">
      <li v-for="n in skeletons" :key="n">
        <KSkeleton shape="block" :class="layout.skeleton" />
      </li>
    </template>
    <slot v-else />
  </ul>
</template>
