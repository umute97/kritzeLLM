<script setup lang="ts" generic="K extends StatusKind = 'page'">
import { computed } from 'vue'

import KChip from './KChip.vue'
import {
  jobStatusLabels,
  jobStatusTones,
  pageStatusLabels,
  pageStatusTones,
  uploadStatusLabels,
  uploadStatusTones,
  type JobStatus,
  type PageStatus,
  type StatusKind,
  type Tone,
  type UploadStatus,
} from './types'

// A page's, a job's or an upload's status, in words and a hint of colour. `kind` (page unless it
// says otherwise) decides which statuses `status` may be.
const props = withDefaults(
  defineProps<{
    status: K extends 'job' ? JobStatus : K extends 'upload' ? UploadStatus : PageStatus
    kind?: K
    size?: 'md' | 'sm'
    label?: string
  }>(),
  { kind: undefined, size: 'md', label: undefined },
)

const tables = {
  page: { tones: pageStatusTones, labels: pageStatusLabels },
  job: { tones: jobStatusTones, labels: jobStatusLabels },
  upload: { tones: uploadStatusTones, labels: uploadStatusLabels },
}
const looks = computed(() => tables[props.kind ?? 'page'])
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
