<script setup lang="ts" generic="K extends StatusKind = 'page'">
import { computed } from 'vue'

import KChip from './KChip.vue'
import { useUiMessages } from './messages'
import {
  pageStatusTones,
  uploadStatusTones,
  type PageStatus,
  type StatusKind,
  type Tone,
  type UploadStatus,
} from './types'

// A page's or an upload's status, in words and a hint of colour. `kind` (page unless it says
// otherwise) decides which statuses `status` may be.
const props = withDefaults(
  defineProps<{
    status: K extends 'upload' ? UploadStatus : PageStatus
    kind?: K
    size?: 'md' | 'sm'
    label?: string
  }>(),
  { size: 'md' },
)

const ui = useUiMessages()

const looks = computed(() =>
  props.kind === 'upload'
    ? { tones: uploadStatusTones, labels: ui.value.uploadStatus }
    : { tones: pageStatusTones, labels: ui.value.pageStatus },
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
