<script setup lang="ts" generic="K extends StatusKind = 'page'">
import { computed } from 'vue'

import KChip from './KChip.vue'
import { useUiMessages } from './messages'
import {
  jobStatusTones,
  pageStatusTones,
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

const ui = useUiMessages()

const looks = computed(() => {
  const kind = props.kind ?? 'page'
  const tones = { page: pageStatusTones, job: jobStatusTones, upload: uploadStatusTones }[kind]
  const labels = {
    page: ui.value.pageStatus,
    job: ui.value.jobStatus,
    upload: ui.value.uploadStatus,
  }[kind]
  return { tones, labels }
})
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
