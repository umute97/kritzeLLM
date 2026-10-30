<script setup lang="ts">
import { computed, ref } from 'vue'

import type { IconName } from './icons'
import KButton from './KButton.vue'
import KIconBadge from './KIconBadge.vue'
import KIconButton from './KIconButton.vue'
import KProgressBar from './KProgressBar.vue'
import KSpinner from './KSpinner.vue'
import type { ToastTone } from './toasts'
import { intentLooks } from './tones'
import { useUiMessages } from './messages'

const props = withDefaults(
  defineProps<{
    tone: ToastTone
    title: string
    detail?: string
    /** Behind "Show details", e.g. the status of an API problem. */
    technical?: string
    icon?: IconName
    actionLabel?: string
    progress?: { value: number; max: number }
    dismissible?: boolean
  }>(),
  { dismissible: undefined },
)

const emit = defineEmits<{ dismiss: []; action: [] }>()

const open = ref(false)

const look = computed(() =>
  props.tone === 'loading'
    ? { ...intentLooks.info, badge: 'bg-lemon text-ink' }
    : intentLooks[props.tone],
)
const canDismiss = computed(() => props.dismissible ?? props.tone !== 'loading')

const ui = useUiMessages()
</script>

<template>
  <div
    :role="tone === 'error' ? 'alert' : 'status'"
    :class="[
      'flex items-start gap-3 rounded-card py-3.5 pr-2.5 pl-3.5',
      tone === 'error' ? 'shadow-bark' : 'shadow-soft',
      look.card,
    ]"
  >
    <KIconBadge :icon="icon ?? look.icon" size="sm" :class="look.badge">
      <KSpinner v-if="tone === 'loading'" :size="18" />
    </KIconBadge>
    <div class="flex min-w-0 flex-1 flex-col gap-0.5">
      <div class="flex items-baseline justify-between gap-2">
        <strong class="text-[15px]">{{ title }}</strong>
        <span v-if="progress" class="shrink-0 pr-1 text-sm text-muted">{{
          ui.progress(progress.value, progress.max)
        }}</span>
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
        v-if="actionLabel || technical || $slots.default"
        class="mt-1.5 flex flex-wrap items-center gap-2"
      >
        <KButton v-if="actionLabel" variant="second" size="sm" @click="emit('action')">
          {{ actionLabel }}
        </KButton>
        <button
          v-if="technical"
          type="button"
          :aria-expanded="open"
          class="min-h-9 cursor-pointer px-2 text-[13px] font-bold text-bark underline underline-offset-3"
          @click="open = !open"
        >
          {{ open ? ui.hideDetails : ui.showDetails }}
        </button>
        <slot />
      </div>
      <code
        v-if="technical && open"
        class="mt-1.5 rounded-lg border border-dashed border-bark bg-paper px-2.5 py-2 font-mono text-xs whitespace-pre-wrap"
        >{{ technical }}</code
      >
    </div>
    <KIconButton
      v-if="canDismiss"
      icon="close"
      :label="ui.dismiss"
      variant="quiet"
      size="sm"
      @click="emit('dismiss')"
    />
  </div>
</template>
