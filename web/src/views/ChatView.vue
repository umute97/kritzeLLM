<script setup lang="ts">
import { computed, onMounted, ref, useId, useTemplateRef, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

import { hasStatus } from '@/api/errors'
import type { Message } from '@/api/types'
import ChatList from '@/components/ChatList.vue'
import ChatRenameDialog from '@/components/ChatRenameDialog.vue'
import ChatSources from '@/components/ChatSources.vue'
import ChatThread from '@/components/ChatThread.vue'
import LostState from '@/components/LostState.vue'
import { useAction } from '@/composables/useAction'
import { useConfirm } from '@/composables/useConfirm'
import { useChat } from '@/stores/chat'
import { useJournals } from '@/stores/journals'
import { KCard, KComposer, KConfirmDialog, KMenu, KPage, type MenuItem } from '@/ui'
import { toastError } from '@/utils/notify'

const props = defineProps<{ conversationId?: string }>()

const { t } = useI18n()
const router = useRouter()
const chat = useChat()
const journals = useJournals()
const titleId = useId()
const threadView = useTemplateRef('threadView')

const thread = computed(() =>
  props.conversationId ? chat.threads.get(props.conversationId) : undefined,
)
const streaming = computed(() => thread.value?.asking?.state === 'streaming')
const title = computed(() => thread.value?.title ?? t('chat.untitled'))

const opening = ref(false)
const missing = ref(false)
/** The citation shown in Sources; without one, Sources follows the latest answer. */
const picked = ref<{ messageId: string; refs: number[] }>()

async function openThread(id: string) {
  opening.value = !chat.threads.has(id)
  try {
    await chat.open(id)
    await threadView.value?.scrollDown(true)
  } catch (error) {
    if (props.conversationId !== id) return
    if (hasStatus(error, 404)) missing.value = true
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

const listChats = useAction(
  () => chat.list(),
  () => ({ title: t('chat.listFailed') }),
)
const moreChats = useAction(
  () => chat.more(),
  () => ({ title: t('chat.listFailed') }),
)

onMounted(() => {
  void listChats.run()
  // Only for the journal's name on source cards, so it can go without.
  journals.loadAll().catch(() => {})
})

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
  await threadView.value?.scrollDown(true)
}

function again() {
  const question = thread.value?.asking?.question
  if (props.conversationId && question) void chat.ask(props.conversationId, question)
}

function stop() {
  if (props.conversationId) chat.stop(props.conversationId)
}

const answers = computed(() => thread.value?.messages.filter((m) => m.role === 'assistant') ?? [])
const shown = computed(
  () => answers.value.find((m) => m.id === picked.value?.messageId) ?? answers.value.at(-1),
)

function cite(message: Message, refs: number[]) {
  picked.value = { messageId: message.id, refs }
}

const renaming = ref(false)
const deleting = useConfirm(
  async () => {
    if (!props.conversationId) return
    await chat.remove(props.conversationId)
    await router.push({ name: 'chat' })
  },
  () => ({ title: t('chat.deleteFailed') }),
)
const menu = computed<MenuItem[]>(() => [
  { id: 'rename', label: t('chat.rename'), icon: 'pencil', run: () => (renaming.value = true) },
  { id: 'delete', label: t('chat.delete'), icon: 'trash', danger: true, run: () => deleting.ask() },
])
</script>

<template>
  <KPage bare class="py-6">
    <div class="grid items-start gap-6 lg:grid-cols-[220px_minmax(0,1fr)_300px]">
      <ChatList
        :chats="chat.chats"
        :current="conversationId"
        :has-more="!!chat.nextCursor"
        :loading="chat.listing"
        @more="moreChats.run()"
      />

      <LostState v-if="missing" :title="t('chat.lostTitle')" :text="t('chat.lost')" />
      <KCard
        v-else
        as="section"
        padding="none"
        :aria-labelledby="titleId"
        class="flex h-[calc(100dvh-12.5rem)] min-h-[28rem] flex-col lg:h-[calc(100dvh-8.5rem)]"
      >
        <header
          class="flex min-h-14 items-center justify-between gap-3 border-b border-line px-5 py-2"
        >
          <h1 :id="titleId" class="m-0 truncate text-xl">{{ title }}</h1>
          <KMenu v-if="thread" :label="t('chat.actions')" :items="menu" />
        </header>

        <ChatThread
          ref="threadView"
          :thread="thread"
          :opening="opening"
          :starting="starting"
          :picked="picked"
          @ask="send"
          @ask-elsewhere="send($event, true)"
          @again="again"
          @cite="cite"
        />

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
      </KCard>

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
      @confirm="deleting.run()"
    />
  </KPage>
</template>
