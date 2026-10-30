<script setup lang="ts">
import { computed } from 'vue'

import type { IconName } from './icons'
import KChip from './KChip.vue'
import KIcon from './KIcon.vue'
import { useUiMessages } from './messages'
import type { Tone } from './types'

type FlagKind = 'unsure' | 'duplicate' | 'edited' | 'saved'

// Little flags on blocks and uploads.
const props = defineProps<{ kind: FlagKind }>()

const ui = useUiMessages()

const flags: Record<FlagKind, { icon?: IconName; tone: Tone; class?: string }> = {
  unsure: {
    icon: 'question',
    tone: 'lemon',
    class: 'border-dashed border-clay!',
  },
  duplicate: { tone: 'orchid' },
  edited: { icon: 'check', tone: 'herb' },
  saved: { icon: 'check', tone: 'herb' },
}

const flag = computed(() => flags[props.kind])
</script>

<template>
  <KChip :tone="flag.tone" :dot="false" size="sm" :class="flag.class">
    <KIcon v-if="flag.icon" :name="flag.icon" :size="13" />
    <slot>{{ ui.flags[kind] }}</slot>
  </KChip>
</template>
