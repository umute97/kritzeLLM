<script setup lang="ts">
import type { Component } from 'vue'

import KPhoto from './KPhoto.vue'
import KProgressBar from './KProgressBar.vue'
import KStatusChip from './KStatusChip.vue'
import type { UploadStatus } from './types'
import { useUiMessages } from './messages'

// One photo in an upload batch, following its page's job from sending to ready.
withDefaults(
  defineProps<{
    fileName: string
    status: UploadStatus
    note?: string
    /** Overrides the chip text, e.g. "Too big". */
    statusLabel?: string
    /** Percent sent, while `status` is `sending`. */
    progress?: number
    as?: string | Component
  }>(),
  { note: undefined, statusLabel: undefined, progress: undefined, as: 'li' },
)

const ui = useUiMessages()
</script>

<template>
  <component
    :is="as"
    :class="[
      'flex flex-wrap items-center gap-x-3 gap-y-2 rounded-field px-3 py-2.5',
      status === 'failed'
        ? 'border-[1.5px] border-bark bg-bark-soft'
        : 'border border-line bg-paper',
    ]"
  >
    <slot name="thumb">
      <KPhoto
        aria-hidden="true"
        class="h-11 w-9 shrink-0 rounded border border-line [--line:8px]"
      />
    </slot>
    <span class="flex min-w-0 flex-[1_1_160px] flex-col leading-snug">
      <strong class="truncate text-sm">{{ fileName }}</strong>
      <span
        v-if="note"
        :class="['text-[13px]', status === 'failed' ? 'text-bark' : 'text-muted']"
        >{{ note }}</span
      >
    </span>
    <KProgressBar
      v-if="status === 'sending' && progress !== undefined"
      class="w-30 shrink-0"
      size="sm"
      :value="progress"
      :label="ui.sending(fileName)"
    />
    <KStatusChip kind="upload" :status="status" :label="statusLabel" size="sm" />
    <slot />
  </component>
</template>
