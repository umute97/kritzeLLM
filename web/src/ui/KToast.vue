<script setup lang="ts">
import { computed, ref } from 'vue'

import type { IconName } from './icons'
import KButton from './KButton.vue'
import KIcon from './KIcon.vue'
import KIconButton from './KIconButton.vue'
import KProgressBar from './KProgressBar.vue'
import KSpinner from './KSpinner.vue'
import type { ToastTone } from './toasts'

const props = withDefaults(
  defineProps<{
    tone: ToastTone
    title: string
    detail?: string
    details?: string
    actionLabel?: string
    progress?: { value: number; max: number }
    dismissible?: boolean
  }>(),
  { dismissible: undefined },
)

const emit = defineEmits<{ dismiss: []; action: [] }>()

const open = ref(false)

const looks: Record<ToastTone, { icon?: IconName; badge: string; card: string }> = {
  success: { icon: 'check', badge: 'bg-herb text-ink', card: 'bg-paper border-[1.5px] border-ink' },
  info: { icon: 'info', badge: 'bg-orchid text-ink', card: 'bg-paper border-[1.5px] border-ink' },
  loading: { badge: 'bg-lemon text-ink', card: 'bg-paper border-[1.5px] border-ink' },
  warning: {
    icon: 'reconnect',
    badge: 'bg-lemon text-ink',
    card: 'bg-lemon-soft border-[1.5px] border-ink',
  },
  error: {
    icon: 'alert',
    badge: 'bg-bark text-cream',
    card: 'bg-bark-soft border-2 border-bark shadow-[0_5px_0_rgb(138_74_58/0.3)]',
  },
}

const look = computed(() => looks[props.tone])
const canDismiss = computed(() => props.dismissible ?? props.tone !== 'loading')
</script>

<template>
  <div
    :role="tone === 'error' ? 'alert' : 'status'"
    :class="['flex items-start gap-3 rounded-card py-3.5 pr-2.5 pl-3.5 shadow-soft', look.card]"
  >
    <span
      aria-hidden="true"
      :class="[
        'flex size-8 shrink-0 items-center justify-center rounded-full border-[1.5px] border-ink',
        look.badge,
      ]"
    >
      <KSpinner v-if="tone === 'loading'" :size="18" />
      <KIcon v-else-if="look.icon" :name="look.icon" :size="16" />
    </span>
    <div class="flex min-w-0 flex-1 flex-col gap-0.5">
      <div class="flex items-baseline justify-between gap-2">
        <strong class="text-[15px]">{{ title }}</strong>
        <span v-if="progress" class="shrink-0 pr-1 text-sm text-muted"
          >{{ progress.value }} of {{ progress.max }}</span
        >
      </div>
      <p
        v-if="detail"
        :class="['text-sm', tone === 'success' || tone === 'info' ? 'text-muted' : '']"
      >
        {{ detail }}
      </p>
      <KProgressBar
        v-if="progress"
        class="mt-2 mr-1"
        size="sm"
        :value="progress.value"
        :max="progress.max"
        :label="title"
      />
      <div
        v-if="actionLabel || details || $slots.default"
        class="mt-1.5 flex flex-wrap items-center gap-2"
      >
        <KButton v-if="actionLabel" variant="second" size="sm" @click="emit('action')">
          {{ actionLabel }}
        </KButton>
        <button
          v-if="details"
          type="button"
          :aria-expanded="open"
          class="min-h-9 cursor-pointer px-2 text-[13px] font-bold text-bark underline underline-offset-3"
          @click="open = !open"
        >
          {{ open ? 'Hide details' : 'Show details' }}
        </button>
        <slot />
      </div>
      <code
        v-if="details && open"
        class="mt-1.5 rounded-lg border border-dashed border-bark bg-paper px-2.5 py-2 font-mono text-xs whitespace-pre-wrap"
        >{{ details }}</code
      >
    </div>
    <KIconButton
      v-if="canDismiss"
      icon="close"
      label="Dismiss"
      variant="plain"
      size="sm"
      @click="emit('dismiss')"
    />
  </div>
</template>
