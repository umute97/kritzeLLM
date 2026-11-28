<script setup lang="ts">
import { computed, nextTick, useTemplateRef, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import type { Message } from '@/api/types'
import ChatAnswer from '@/components/ChatAnswer.vue'
import type { Thread } from '@/stores/chat'
import { KButton, KEmptyState, KMessage, KSkeleton } from '@/ui'

// A chat's messages and the answer on its way. It follows that answer down as it's written,
// unless you scrolled up to read.
const props = defineProps<{
  thread?: Thread
  opening?: boolean
  starting?: boolean
  picked?: { messageId: string; refs: number[] }
}>()

const emit = defineEmits<{
  ask: [question: string]
  askElsewhere: [question: string]
  again: []
  cite: [message: Message, refs: number[]]
}>()

const { t } = useI18n()
const asking = computed(() => props.thread?.asking)

const starters = computed(() => [
  t('chat.starters.one'),
  t('chat.starters.two'),
  t('chat.starters.three'),
])

const failure = computed(() => {
  const problem = asking.value?.problem
  return problem ? (problem.detail ?? problem.title) : t('chat.broke')
})

const scroller = useTemplateRef('scroller')
let following = true

function onScroll() {
  const el = scroller.value
  if (el) following = el.scrollHeight - el.scrollTop - el.clientHeight < 80
}

async function scrollDown(always = false) {
  await nextTick()
  const el = scroller.value
  if (el && (always || following)) el.scrollTop = el.scrollHeight
}

watch(
  () => [
    props.thread?.messages.length,
    asking.value?.text,
    asking.value?.steps.length,
    asking.value?.state,
  ],
  () => void scrollDown(),
)

defineExpose({ scrollDown })
</script>

<template>
  <div
    ref="scroller"
    class="flex flex-1 flex-col gap-4 overflow-y-auto px-5 py-5"
    :aria-busy="opening"
    @scroll="onScroll"
  >
    <template v-if="opening">
      <KSkeleton shape="block" class="h-12 w-2/3 self-end" />
      <KSkeleton shape="block" class="h-24 w-4/5" />
    </template>
    <KEmptyState
      v-else-if="!thread?.messages.length && !asking"
      :title="t('chat.idleTitle')"
      :text="t('chat.idle')"
      :framed="false"
      class="m-auto max-w-md"
    >
      <KButton
        v-for="starter in starters"
        :key="starter"
        variant="second"
        size="sm"
        :disabled="starting"
        @click="emit('ask', starter)"
      >
        {{ starter }}
      </KButton>
    </KEmptyState>

    <template v-for="message in thread?.messages ?? []" :key="message.id">
      <KMessage v-if="message.role === 'user'" author="user">
        <span class="whitespace-pre-line">{{ message.content }}</span>
      </KMessage>
      <ChatAnswer
        v-else
        :content="message.content"
        :steps="message.toolCalls"
        :sources="message.sources"
        :picked="picked?.messageId === message.id ? picked.refs : undefined"
        @cite="emit('cite', message, $event)"
      />
    </template>

    <template v-if="asking">
      <KMessage author="user">
        <span class="whitespace-pre-line">{{ asking.question }}</span>
      </KMessage>
      <KMessage v-if="asking.state === 'full'" author="assistant">
        {{ t('chat.full') }}
        <template #actions>
          <KButton size="sm" :loading="starting" @click="emit('askElsewhere', asking.question)">
            {{ t('chat.askInNew') }}
          </KButton>
        </template>
      </KMessage>
      <template v-else>
        <ChatAnswer
          :content="asking.text"
          :steps="asking.steps"
          :streaming="asking.state === 'streaming'"
        />
        <p v-if="asking.state === 'stopped'" class="m-0 flex flex-wrap items-center gap-3 pl-12">
          <span class="text-sm text-muted">{{ t('chat.stopped') }}</span>
          <KButton variant="second" size="sm" @click="emit('again')">{{
            t('chat.askAgain')
          }}</KButton>
        </p>
        <KMessage v-else-if="asking.state === 'failed'" author="assistant" error>
          {{ failure }}
          <template #actions>
            <KButton variant="second" size="sm" @click="emit('again')">
              {{ t('chat.askAgain') }}
            </KButton>
          </template>
        </KMessage>
      </template>
    </template>
  </div>
</template>
