<script setup lang="ts">
import { computed, ref, useId } from 'vue'
import { useI18n } from 'vue-i18n'

import { KIcon } from '@/ui'
import { lookedFor, stepKind, tally, type Step } from '@/utils/chat'

// What the helper did for an answer, as a footnote in it: one line that unfolds into the steps.
const props = defineProps<{ steps: Step[] }>()

const { t } = useI18n()
const expanded = ref(false)
const listId = useId()

const summary = computed(() => {
  const { searches, reads, browses } = tally(props.steps)
  const parts: string[] = []
  if (searches === 1) parts.push(t('chat.summary.once'))
  else if (searches === 2) parts.push(t('chat.summary.twice'))
  else if (searches > 2) parts.push(t('chat.summary.times', { n: searches }))
  if (browses) parts.push(t('chat.summary.browsed'))
  if (reads) parts.push(t('chat.summary.read', reads))
  const text = parts.join(' · ') || t('chat.summary.other')
  return text.charAt(0).toLocaleUpperCase() + text.slice(1)
})

function item(step: Step): string {
  return t(`chat.steps.${stepKind(step.name)}.listed`, {
    query: lookedFor(step),
    pages: t('chat.found', step.pages ?? 0),
  })
}
</script>

<template>
  <div class="flex flex-col text-[13px] text-muted">
    <button
      type="button"
      :aria-expanded="expanded"
      :aria-controls="expanded ? listId : undefined"
      class="flex min-h-8 cursor-pointer items-center gap-1.5 self-start font-semibold"
      @click="expanded = !expanded"
    >
      <KIcon name="search" :size="15" />
      {{ summary }}
      <KIcon name="chevron-down" :size="13" :class="expanded && 'rotate-180'" />
    </button>
    <ol v-if="expanded" :id="listId" class="mb-2 flex list-decimal flex-col gap-0.5 pl-5">
      <li v-for="step in steps" :key="step.id">{{ item(step) }}</li>
    </ol>
  </div>
</template>
