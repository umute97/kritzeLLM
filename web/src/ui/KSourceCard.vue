<script setup lang="ts">
import KHighlight from './KHighlight.vue'
import KIcon from './KIcon.vue'
import { useLinkComponent } from './plugin'
import { linkAttrs, type LinkTarget } from './polymorphic'
import { useUiMessages } from './messages'

// A cited page in the Sources panel. The picked one lifts and its quote takes the accent.
withDefaults(
  defineProps<{
    title: string
    date?: string
    before?: string
    quote: string
    after?: string
    selected?: boolean
    to?: LinkTarget
    linkLabel?: string
  }>(),
  {
    date: undefined,
    before: '',
    after: '',
    to: undefined,
    linkLabel: undefined,
  },
)

const link = useLinkComponent()

const ui = useUiMessages()
</script>

<template>
  <div
    :class="[
      'flex flex-col gap-2.5 rounded-field bg-paper p-3',
      selected ? 'border-2 border-ink shadow-soft' : 'border border-line',
    ]"
  >
    <div class="flex items-baseline justify-between gap-2">
      <strong class="text-[15px]">{{ title }}</strong>
      <span v-if="date" class="text-[13px] text-muted">{{ date }}</span>
    </div>
    <p
      class="paper-lines m-0 rounded border border-sand px-3 py-2.5 font-hand text-[19px] leading-[26px] [--line:26px]"
    >
      <KHighlight :before="before" :hit="quote" :after="after" :soft="!selected" />
    </p>
    <component
      :is="link"
      v-if="to"
      v-bind="linkAttrs(link, to)"
      class="inline-flex items-center gap-1.5 self-start text-sm font-bold"
    >
      {{ linkLabel ?? ui.openPage }}
      <KIcon name="chevron-right" :size="16" />
    </component>
  </div>
</template>
