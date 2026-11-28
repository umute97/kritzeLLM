<script setup lang="ts">
import { computed, ref, useId } from 'vue'

import type { IconName } from './icons'
import KButton from './KButton.vue'
import KDisclosure from './KDisclosure.vue'
import KIconBadge from './KIconBadge.vue'
import KIconButton from './KIconButton.vue'
import type { ToastTone } from './toasts'
import { intentLooks } from './tones'
import { useUiMessages } from './messages'

const props = defineProps<{
  tone: ToastTone
  title: string
  detail?: string
  /** Behind "Show details", e.g. the status of an API problem. */
  technical?: string
  icon?: IconName
  actionLabel?: string
}>()

const emit = defineEmits<{ dismiss: []; action: [] }>()

const open = ref(false)
const technicalId = useId()
const look = computed(() => intentLooks[props.tone])

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
    <KIconBadge :icon="icon ?? look.icon" size="sm" :class="look.badge" />
    <div class="flex min-w-0 flex-1 flex-col gap-0.5">
      <strong class="text-[15px]">{{ title }}</strong>
      <p
        v-if="detail"
        :class="['text-sm', tone === 'success' || tone === 'info' ? 'text-muted' : '']"
      >
        {{ detail }}
      </p>
      <div
        v-if="actionLabel || technical || $slots.default"
        class="mt-1.5 flex flex-wrap items-center gap-2"
      >
        <KButton v-if="actionLabel" variant="second" size="sm" @click="emit('action')">
          {{ actionLabel }}
        </KButton>
        <KDisclosure
          v-if="technical"
          v-model:open="open"
          :controls="open ? technicalId : undefined"
          variant="quiet"
        >
          {{ open ? ui.hideDetails : ui.showDetails }}
        </KDisclosure>
        <slot />
      </div>
      <code
        v-if="technical && open"
        :id="technicalId"
        class="mt-1.5 rounded-lg border border-dashed border-bark bg-paper px-2.5 py-2 font-mono text-xs whitespace-pre-wrap"
        >{{ technical }}</code
      >
    </div>
    <KIconButton
      icon="close"
      :label="ui.dismiss"
      variant="quiet"
      size="sm"
      @click="emit('dismiss')"
    />
  </div>
</template>
