<script setup lang="ts">
import { computed } from 'vue'

import KChip from './KChip.vue'
import {
  jobStatusLabels,
  jobStatusTones,
  pageStatusLabels,
  pageStatusTones,
  type JobStatus,
  type PageStatus,
} from './types'

// A page's or a job's status, in words and a hint of colour.
const props = withDefaults(
  defineProps<{
    status: PageStatus | JobStatus
    kind?: 'page' | 'job'
    size?: 'md' | 'sm'
    label?: string
  }>(),
  { kind: 'page', size: 'md', label: undefined },
)

const tone = computed(() =>
  props.kind === 'job'
    ? jobStatusTones[props.status as JobStatus]
    : pageStatusTones[props.status as PageStatus],
)
const text = computed(
  () =>
    props.label ??
    (props.kind === 'job'
      ? jobStatusLabels[props.status as JobStatus]
      : pageStatusLabels[props.status as PageStatus]),
)
</script>

<template>
  <KChip :tone="tone" :size="size">{{ text }}</KChip>
</template>
