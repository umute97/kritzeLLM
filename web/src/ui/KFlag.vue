<script setup lang="ts">
import { computed } from 'vue'

import type { IconName } from './icons'
import KChip from './KChip.vue'
import KIcon from './KIcon.vue'
import type { Tone } from './types'

type FlagKind = 'unsure' | 'duplicate' | 'edited' | 'saved'

// Little flags on blocks and uploads.
const props = defineProps<{ kind: FlagKind }>()

const flags: Record<FlagKind, { text: string; icon?: IconName; tone: Tone; class?: string }> = {
  unsure: {
    text: 'not quite sure',
    icon: 'question',
    tone: 'lemon',
    class: 'border-dashed border-clay!',
  },
  duplicate: { text: 'already here', tone: 'orchid' },
  edited: { text: 'edited by you', icon: 'check', tone: 'herb' },
  saved: { text: 'saved', icon: 'check', tone: 'herb' },
}

const flag = computed(() => flags[props.kind])
</script>

<template>
  <KChip :tone="flag.tone" :dot="false" size="sm" :class="flag.class">
    <KIcon v-if="flag.icon" :name="flag.icon" :size="13" />
    <slot>{{ flag.text }}</slot>
  </KChip>
</template>
