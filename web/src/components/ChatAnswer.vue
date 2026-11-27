<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import type { Source } from '@/api/types'
import ChatSteps from '@/components/ChatSteps.vue'
import { KCitationChip, KMessage, KToolActivity } from '@/ui'
import { chips, lookedFor, paragraphs, stepKind, type Step } from '@/utils/chat'

// An answer. Before its first word, a line beside the dots flips through what the helper does;
// then its text with a chip per cited page (dashed until the saved answer brings the sources),
// and once it's done, a footnote of the steps it took.
const props = defineProps<{
  content: string
  steps: Step[]
  sources?: Source[]
  streaming?: boolean
  picked?: number[]
}>()

const emit = defineEmits<{ cite: [refs: number[]] }>()

const { t } = useI18n()
const text = computed(() => paragraphs(props.content))
const byRef = computed(() => new Map(props.sources?.map((source) => [source.ref, source])))

const doing = computed(() => {
  const step = props.steps.at(-1)
  if (!step) return t('chat.thinking')
  return t(`chat.steps.${stepKind(step.name)}.${step.pages === undefined ? 'working' : 'done'}`, {
    query: lookedFor(step),
    pages: t('chat.found', step.pages ?? 0),
  })
})
</script>

<template>
  <KMessage v-if="streaming && !content" author="assistant" typing>
    <KToolActivity :text="doing" />
  </KMessage>
  <KMessage v-else-if="content" author="assistant" :streaming="streaming">
    <!-- The last paragraph stays inline, so the caret follows its words. -->
    <span
      v-for="(pieces, index) in text"
      :key="index"
      :class="['whitespace-pre-line', index < text.length - 1 && 'mb-3 block']"
    >
      <template v-for="(piece, at) in pieces" :key="at">
        <template v-if="'text' in piece">{{ piece.text }}</template>
        <KCitationChip v-else-if="!sources" :label="t('chat.citeWaiting')" disabled />
        <template v-else>
          <KCitationChip
            v-for="chip in chips(piece.refs, byRef)"
            :key="chip.source.ref"
            :label="t('chat.cite', { n: chip.source.pageNumber })"
            :selected="chip.refs.some((ref) => picked?.includes(ref))"
            @click="emit('cite', chip.refs)"
          />
        </template>
      </template>
    </span>
    <template v-if="steps.length && !streaming" #footer>
      <ChatSteps :steps="steps" />
    </template>
  </KMessage>
</template>
