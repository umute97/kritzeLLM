<script setup lang="ts">
import { computed, type Component } from 'vue'

import KButton from './KButton.vue'
import KSpinner from './KSpinner.vue'
import KStatusChip from './KStatusChip.vue'
import type { PageStatus } from './types'

// A page pinned to the board. Without a photo yet it shows lined paper (and an excerpt if any).
// Attributes such as `href` or `to` go to the link, not the outer frame.
defineOptions({ inheritAttrs: false })

const props = withDefaults(
  defineProps<{
    pageNumber: number
    status: PageStatus
    date?: string
    imageUrl?: string
    excerpt?: string
    /** Degrees; see `tiltFor()`. */
    tilt?: number
    selected?: boolean
    failedText?: string
    as?: string | Component
  }>(),
  {
    date: undefined,
    imageUrl: undefined,
    excerpt: undefined,
    tilt: 0,
    failedText: 'couldn’t read this one',
    as: 'a',
  },
)

const emit = defineEmits<{ retry: [] }>()

const reading = computed(() =>
  props.status === 'uploaded' ? 'waiting…' : props.status === 'transcribing' ? 'reading…' : null,
)
const failed = computed(() => props.status === 'failed')
</script>

<template>
  <div
    class="group relative rotate-(--tilt) transition-[rotate,translate] duration-150 focus-within:rotate-0 hover:-translate-y-1 hover:rotate-0"
    :style="{ '--tilt': `${tilt}deg` }"
  >
    <component
      :is="as"
      v-bind="$attrs"
      :class="[
        'flex flex-col gap-2.5 rounded-field bg-paper p-3 pb-3.5 text-ink no-underline hover:text-ink',
        selected
          ? 'border-[2.5px] border-ink shadow-[0_8px_0_var(--color-ink)]'
          : 'border border-line shadow-pin group-hover:border-ink group-hover:shadow-[0_8px_0_var(--color-ink)]',
      ]"
    >
      <span class="relative block h-[190px] overflow-hidden rounded border border-sand">
        <img
          v-if="imageUrl"
          :src="imageUrl"
          alt=""
          loading="lazy"
          class="size-full object-cover"
          :class="(reading || failed) && 'opacity-35'"
        />
        <span
          v-else
          class="paper-lines block size-full p-3 font-hand text-[15px] leading-6"
          :class="(reading || failed) && 'opacity-35'"
          >{{ excerpt }}</span
        >
        <span
          v-if="reading"
          class="absolute inset-0 flex flex-col items-center justify-center gap-1.5 bg-paper/55"
        >
          <KSpinner :size="26" class="text-ink" />
          <span class="font-hand text-xl text-bark">{{ reading }}</span>
        </span>
      </span>
      <span class="flex items-center justify-between gap-2">
        <span class="flex flex-col leading-tight">
          <strong class="text-sm">Page {{ pageNumber }}</strong>
          <span v-if="date" class="text-[13px] text-muted">{{ date }}</span>
        </span>
        <KStatusChip :status="status" size="sm" />
      </span>
    </component>
    <div
      v-if="failed"
      class="absolute inset-x-3 top-3 flex h-[190px] flex-col items-center justify-center gap-2 rounded bg-bark-soft/85 p-2.5 text-center"
    >
      <span class="font-hand text-xl leading-tight text-bark">{{ failedText }}</span>
      <KButton variant="second" size="sm" @click="emit('retry')">Try again</KButton>
    </div>
  </div>
</template>
