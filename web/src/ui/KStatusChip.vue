<script setup lang="ts" generic="K extends 'page' | 'job' = 'page'">
import { computed } from 'vue'

import KChip from './KChip.vue'
import {
  jobStatusLabels,
  jobStatusTones,
  pageStatusLabels,
  pageStatusTones,
  type JobStatus,
  type PageStatus,
  type Tone,
} from './types'

// A page's or a job's status, in words and a hint of colour. `kind` (page unless it says job)
// decides which statuses `status` may be.
const props = withDefaults(
  defineProps<{
    status: K extends 'job' ? JobStatus : PageStatus
    kind?: K
    size?: 'md' | 'sm'
    label?: string
  }>(),
  { kind: undefined, size: 'md', label: undefined },
)

const looks = computed(() =>
  props.kind === 'job'
    ? { tones: jobStatusTones, labels: jobStatusLabels }
    : { tones: pageStatusTones, labels: pageStatusLabels },
)
const tone = computed<Tone>(
  () => (looks.value.tones as Record<string, Tone>)[props.status] ?? 'plain',
)
const text = computed(
  () => props.label ?? (looks.value.labels as Record<string, string>)[props.status] ?? props.status,
)
</script>

<template>
  <KChip :tone="tone" :size="size">{{ text }}</KChip>
</template>
