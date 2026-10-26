<script setup lang="ts">
import { computed } from 'vue'

import KChip from './KChip.vue'
import KProgressBar from './KProgressBar.vue'
import type { Tone, UploadStatus } from './types'

// One photo in an upload batch, following its page's job from sending to ready.
const props = defineProps<{
  fileName: string
  status: UploadStatus
  note?: string
  /** Overrides the chip text, e.g. "Too big". */
  statusLabel?: string
  /** Percent sent, while `status` is `sending`. */
  progress?: number
}>()

const chips: Record<UploadStatus, { label: string; tone: Tone }> = {
  sending: { label: 'Sending', tone: 'plain' },
  queued: { label: 'Waiting', tone: 'plain' },
  transcribing: { label: 'Transcribing', tone: 'lemon' },
  indexing: { label: 'Indexing', tone: 'orchid' },
  ready: { label: 'Ready', tone: 'herb' },
  duplicate: { label: 'Already here', tone: 'orchid' },
  failed: { label: 'Failed', tone: 'bark' },
  deleted: { label: 'Deleted', tone: 'plain' },
}

const chip = computed(() => chips[props.status])
const failed = computed(() => props.status === 'failed')
</script>

<template>
  <li
    :class="[
      'flex flex-wrap items-center gap-x-3 gap-y-2 rounded-field px-3 py-2.5',
      failed ? 'border-[1.5px] border-bark bg-bark-soft' : 'border border-line bg-paper',
    ]"
  >
    <span
      aria-hidden="true"
      class="paper-lines h-11 w-9 shrink-0 rounded border border-line [--line:8px]"
    />
    <span class="flex min-w-0 flex-[1_1_160px] flex-col leading-snug">
      <strong class="truncate text-sm">{{ fileName }}</strong>
      <span v-if="note" :class="['text-[13px]', failed ? 'text-bark' : 'text-muted']">{{
        note
      }}</span>
    </span>
    <KProgressBar
      v-if="status === 'sending' && progress !== undefined"
      class="w-30 shrink-0"
      size="sm"
      :value="progress"
      :label="`Sending ${fileName}`"
    />
    <KChip :tone="chip.tone" size="sm">{{ statusLabel ?? chip.label }}</KChip>
    <slot />
  </li>
</template>
