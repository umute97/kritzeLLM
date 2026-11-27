<script setup lang="ts">
import { computed, nextTick, onMounted, ref, useId, useTemplateRef, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

import { ApiError } from '@/api/errors'
import type { Message } from '@/api/types'
import ChatAnswer from '@/components/ChatAnswer.vue'
import ChatList from '@/components/ChatList.vue'
import ChatRenameDialog from '@/components/ChatRenameDialog.vue'
import ChatSources from '@/components/ChatSources.vue'
import LostState from '@/components/LostState.vue'
import { useConfirm } from '@/composables/useConfirm'
import { useChat } from '@/stores/chat'
import { useJournals } from '@/stores/journals'
import {
  KButton,
  KComposer,
  KConfirmDialog,
  KMenu,
  KMessage,
  KPage,
  KSkeleton,
  type MenuItem,
} from '@/ui'
import type { Step } from '@/utils/chat'
import { toastError } from '@/utils/notify'

const props = defineProps<{ conversationId?: string }>()

const { t } = useI18n()
const router = useRouter()
const chat = useChat()
const journals = useJournals()
const titleId = useId()

const thread = computed(() =>
  props.conversationId ? chat.threads.get(props.conversationId) : undefined,
)
const asking = computed(() => thread.value?.asking)
const streaming = computed(() => asking.value?.state === 'streaming')
const title = computed(() => thread.value?.title ?? t('chat.untitled'))

const opening = ref(false)
const missing = ref(false)
/** The citation shown in Sources; without one, Sources follows the latest answer. */
const picked = ref<{ messageId: string; refs: number[] }>()

async function openThread(id: string) {
  opening.value = !chat.threads.has(id)
  try {
    await chat.open(id)
    await scrollDown(true)
  } catch (error) {
    if (props.conversationId !== id) return
    if (error instanceof ApiError && error.status === 404) missing.value = true
    else toastError(error, t('chat.openFailed'), { retry: () => void openThread(id) })
  } finally {
    if (props.conversationId === id) opening.value = false
  }
}

watch(
  () => props.conversationId,
  (id) => {
    picked.value = undefined
    missing.value = false
    if (id) void openThread(id)
  },
  { immediate: true },
)

onMounted(async () => {
  try {
    await chat.list()
  } catch (error) {
    toastError(error, t('chat.listFailed'))
  }
  // Only for the journal's name on source cards, so it can go without.
  journals.all().catch(() => {})
})

async function more() {
  try {
    await chat.more()
  } catch (error) {
    toastError(error, t('chat.listFailed'))
  }
}

const draft = ref('')
const starting = ref(false)

/** Asks in this chat, or in a new one: a fresh chat, or one that's full (`elsewhere`). */
async function send(question: string, elsewhere = false) {
  draft.value = ''
  picked.value = undefined
  let id = elsewhere ? undefined : props.conversationId
  if (!id) {
    starting.value = true
    try {
      id = (await chat.start()).id
    } catch (error) {
      draft.value = question
      toastError(error, t('chat.startFailed'))
      return
    } finally {
      starting.value = false
    }
    void chat.ask(id, question)
    // A fresh chat becomes this one; a full one stays in the history.
    await router[elsewhere ? 'push' : 'replace']({ name: 'chat', params: { conversationId: id } })
  } else {
    void chat.ask(id, question)
  }
  await scrollDown(true)
}

function again() {
  if (props.conversationId && asking.value)
    void chat.ask(props.conversationId, asking.value.question)
}

function stop() {
  if (props.conversationId) chat.stop(props.conversationId)
}

const starters = computed(() => [
  t('chat.starters.one'),
  t('chat.starters.two'),
  t('chat.starters.three'),
])

function stepsOf(message: Message): Step[] {
  return message.toolCalls.map((call, index) => ({ id: String(index), ...call }))
}

const failure = computed(() => {
  const problem = asking.value?.problem
  return problem ? (problem.detail ?? problem.title) : t('chat.broke')
})

const answers = computed(() => thread.value?.messages.filter((m) => m.role === 'assistant') ?? [])
const shown = computed(
  () => answers.value.find((m) => m.id === picked.value?.messageId) ?? answers.value.at(-1),
)

function cite(message: Message, refs: number[]) {
  picked.value = { messageId: message.id, refs }
}

// Follows the answer down as it's written, unless you scrolled up to read.
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
    thread.value?.messages.length,
    asking.value?.text,
    asking.value?.steps.length,
    asking.value?.state,
  ],
  () => void scrollDown(),
)

const renaming = ref(false)
const deleting = useConfirm()
const menu = computed<MenuItem[]>(() => [
  { id: 'rename', label: t('chat.rename'), icon: 'pencil', run: () => (renaming.value = true) },
  { id: 'delete', label: t('chat.delete'), icon: 'trash', danger: true, run: () => deleting.ask() },
])

async function deleteChat() {
  const id = props.conversationId
  if (!id) return
  await deleting.run(
    async () => {
      await chat.remove(id)
      await router.push({ name: 'chat' })
    },
    { title: t('chat.deleteFailed') },
  )
}
</script>

<template>
  <KPage bare class="py-6">
    <div class="grid items-start gap-6 lg:grid-cols-[220px_minmax(0,1fr)_300px]">
      <ChatList
        :chats="chat.chats"
        :current="conversationId"
        :has-more="!!chat.nextCursor"
        :loading="chat.listing"
        @more="more"
      />

      <LostState v-if="missing" :title="t('chat.lostTitle')" :text="t('chat.lost')" />
      <section
        v-else
        :aria-labelledby="titleId"
        class="flex h-[calc(100dvh-12.5rem)] min-h-[28rem] flex-col lg:h-[calc(100dvh-8.5rem)] rounded-card border-[1.5px] border-ink bg-paper"
      >
        <header
          class="flex min-h-14 items-center justify-between gap-3 border-b border-line px-5 py-2"
        >
          <h1 :id="titleId" class="m-0 truncate text-xl">{{ title }}</h1>
          <KMenu v-if="thread" :label="t('chat.actions')" :items="menu" />
        </header>

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
          <div
            v-else-if="!thread?.messages.length && !asking"
            class="m-auto flex max-w-md flex-col items-center gap-4 text-center"
          >
            <h2 class="m-0 text-3xl">{{ t('chat.idleTitle') }}</h2>
            <p class="m-0 font-hand text-[19px] text-bark">{{ t('chat.idle') }}</p>
            <ul class="flex flex-wrap justify-center gap-2">
              <li v-for="starter in starters" :key="starter">
                <KButton variant="second" size="sm" :disabled="starting" @click="send(starter)">
                  {{ starter }}
                </KButton>
              </li>
            </ul>
          </div>

          <template v-for="message in thread?.messages ?? []" :key="message.id">
            <KMessage v-if="message.role === 'user'" author="user">
              <span class="whitespace-pre-line">{{ message.content }}</span>
            </KMessage>
            <ChatAnswer
              v-else
              :content="message.content"
              :steps="stepsOf(message)"
              :sources="message.sources"
              :picked="picked?.messageId === message.id ? picked.refs : undefined"
              @cite="cite(message, $event)"
            />
          </template>

          <template v-if="asking">
            <KMessage author="user">
              <span class="whitespace-pre-line">{{ asking.question }}</span>
            </KMessage>
            <KMessage v-if="asking.state === 'full'" author="assistant">
              {{ t('chat.full') }}
              <template #actions>
                <KButton size="sm" :loading="starting" @click="send(asking.question, true)">
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
              <p
                v-if="asking.state === 'stopped'"
                class="m-0 flex flex-wrap items-center gap-3 pl-12"
              >
                <span class="text-sm text-muted">{{ t('chat.stopped') }}</span>
                <KButton variant="second" size="sm" @click="again">{{
                  t('chat.askAgain')
                }}</KButton>
              </p>
              <KMessage v-else-if="asking.state === 'failed'" author="assistant" error>
                {{ failure }}
                <template #actions>
                  <KButton variant="second" size="sm" @click="again">
                    {{ t('chat.askAgain') }}
                  </KButton>
                </template>
              </KMessage>
            </template>
          </template>
        </div>

        <div class="p-3">
          <KComposer
            v-model="draft"
            :label="t('chat.label')"
            :placeholder="t('chat.placeholder')"
            :streaming="streaming"
            :disabled="opening || starting"
            maxlength="4000"
            @send="send"
            @stop="stop"
          />
        </div>
      </section>

      <ChatSources
        :sources="shown?.sources ?? []"
        :picked="shown && picked?.messageId === shown.id ? picked.refs : undefined"
        class="lg:sticky lg:top-6"
      />
    </div>

    <ChatRenameDialog v-model:open="renaming" :conversation="thread" />
    <KConfirmDialog
      v-model:open="deleting.open"
      :title="t('chat.deleteTitle')"
      :description="t('chat.deleteNote')"
      :confirm-label="t('chat.delete')"
      :loading="deleting.busy"
      @confirm="deleteChat"
    />
  </KPage>
</template>
