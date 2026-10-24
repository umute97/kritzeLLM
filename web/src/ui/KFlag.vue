<script setup lang="ts">
import { computed } from 'vue'

import type { IconName } from './icons'
import KIcon from './KIcon.vue'

type FlagKind = 'unsure' | 'duplicate' | 'edited' | 'saved'

// Little flags on blocks and uploads.
const props = defineProps<{ kind: FlagKind }>()

const flags: Record<FlagKind, { text: string; icon?: IconName; class: string }> = {
  unsure: {
    text: 'not quite sure',
    icon: 'question',
    class: 'bg-lemon-soft border-dashed border-clay',
  },
  duplicate: { text: 'already here', class: 'bg-orchid-soft border-orchid' },
  edited: { text: 'edited by you', icon: 'check', class: 'bg-herb-soft border-herb' },
  saved: { text: 'saved', icon: 'check', class: 'bg-herb-soft border-herb' },
}

const flag = computed(() => flags[props.kind])
</script>

<template>
  <span
    :class="[
      'inline-flex shrink-0 items-center gap-1 rounded-full border px-2.5 py-px text-xs font-bold whitespace-nowrap text-ink',
      flag.class,
    ]"
  >
    <KIcon v-if="flag.icon" :name="flag.icon" :size="13" />
    <slot>{{ flag.text }}</slot>
  </span>
</template>
