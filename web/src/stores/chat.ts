import { defineStore } from 'pinia'
import { markRaw, reactive, ref } from 'vue'

import { streamAnswer } from '@/api/chat'
import { api, call, isAbort } from '@/api/client'
import { ApiError, hasStatus } from '@/api/errors'
import type {
  ChatStreamEvent,
  Conversation,
  ConversationDetail,
  Message,
  Problem,
} from '@/api/types'
import type { Step } from '@/utils/chat'

export const CHATS_BATCH = 25

/**
 * A question being answered, or one whose answer didn't make it. The server saves a question
 * only together with its answer, so none of this is kept once it's not streaming any more.
 */
export interface Asking {
  question: string
  text: string
  steps: Step[]
  state: 'streaming' | 'stopped' | 'failed' | 'full'
  /** Why it failed; none when the stream just broke off. */
  problem?: Problem
  controller: AbortController
}

export interface Thread {
  id: string
  title: string | null
  messages: Message[]
  asking?: Asking
}

/**
 * The chats: the list of earlier ones, and every opened one with its messages. An answer keeps
 * streaming into its thread while you look at another chat.
 */
export const useChat = defineStore('chat', () => {
  const chats = ref<Conversation[]>([])
  const nextCursor = ref<string | null>(null)
  const listing = ref(false)
  const threads = reactive(new Map<string, Thread>())

  /** Adds or moves a chat to its place in the list: most recently active first. */
  function put({ id, title, createdAt, updatedAt }: Conversation) {
    const rest = chats.value.filter((known) => known.id !== id)
    const at = rest.findIndex((known) => Date.parse(known.updatedAt) < Date.parse(updatedAt))
    rest.splice(at === -1 ? rest.length : at, 0, { id, title, createdAt, updatedAt })
    chats.value = rest
  }

  async function fetchChats(cursor?: string) {
    listing.value = true
    try {
      return await call(
        api.GET('/conversations', { params: { query: { limit: CHATS_BATCH, cursor } } }),
      )
    } finally {
      listing.value = false
    }
  }

  async function list() {
    const page = await fetchChats()
    chats.value = page.items
    nextCursor.value = page.nextCursor
  }

  async function more() {
    if (!nextCursor.value) return
    const page = await fetchChats(nextCursor.value)
    // A chat that moved up since the first batch comes again further down.
    const known = new Set(chats.value.map((chat) => chat.id))
    chats.value = [...chats.value, ...page.items.filter((chat) => !known.has(chat.id))]
    nextCursor.value = page.nextCursor
  }

  function remember(detail: ConversationDetail): Thread {
    const thread = threads.get(detail.id)
    if (!thread) {
      threads.set(detail.id, { id: detail.id, title: detail.title, messages: detail.messages })
      return threads.get(detail.id)!
    }
    thread.title = detail.title
    if (thread.asking?.state !== 'streaming') thread.messages = detail.messages
    return thread
  }

  async function fetchThread(id: string): Promise<Thread> {
    const detail = await call(
      api.GET('/conversations/{conversationId}', { params: { path: { conversationId: id } } }),
    )
    put(detail)
    return remember(detail)
  }

  /** A chat with its messages: at once when it's been opened before (and refreshed behind). */
  async function open(id: string): Promise<Thread> {
    const known = threads.get(id)
    if (!known) return fetchThread(id)
    if (known.asking?.state !== 'streaming') void fetchThread(id).catch(() => {})
    return known
  }

  /** A new, empty chat. It takes its title from its first question. */
  async function start(): Promise<Thread> {
    const conversation = await call(api.POST('/conversations', { body: {} }))
    put(conversation)
    threads.set(conversation.id, { id: conversation.id, title: conversation.title, messages: [] })
    return threads.get(conversation.id)!
  }

  function follow(asking: Asking, event: ChatStreamEvent) {
    if (event.type === 'textDelta') asking.text += event.text
    else if (event.type === 'toolCall') {
      asking.steps.push({ id: event.id, name: event.name, args: event.args })
    } else if (event.type === 'toolResult') {
      const step = asking.steps.find((known) => known.id === event.id)
      if (step) step.pages = event.pages
    }
  }

  /** Asks a question in a chat and follows its answer as it streams. */
  async function ask(id: string, question: string) {
    const thread = threads.get(id)
    if (!thread || thread.asking?.state === 'streaming') return
    const asking = reactive<Asking>({
      question,
      text: '',
      steps: [],
      state: 'streaming',
      controller: markRaw(new AbortController()),
    })
    thread.asking = asking
    try {
      const answer = await streamAnswer(id, question, {
        signal: asking.controller.signal,
        onEvent: (event) => follow(asking, event),
      })
      const asked: Message = {
        id: `${answer.id}:question`,
        role: 'user',
        content: question,
        toolCalls: [],
        sources: [],
        createdAt: answer.createdAt,
      }
      thread.messages.push(asked, answer)
      thread.asking = undefined
      // For the title it got from this question, and its new place in the list.
      void fetchThread(id).catch(() => {})
    } catch (error) {
      if (isAbort(error)) asking.state = 'stopped'
      else if (hasStatus(error, 409)) asking.state = 'full'
      else asking.state = 'failed'
      if (error instanceof ApiError) asking.problem = error.problem
    }
  }

  function stop(id: string) {
    threads.get(id)?.asking?.controller.abort()
  }

  async function rename(id: string, title: string | null) {
    const conversation = await call(
      api.PATCH('/conversations/{conversationId}', {
        params: { path: { conversationId: id } },
        body: { title },
      }),
    )
    put(conversation)
    const thread = threads.get(id)
    if (thread) thread.title = conversation.title
  }

  async function remove(id: string) {
    stop(id)
    await call(
      api.DELETE('/conversations/{conversationId}', { params: { path: { conversationId: id } } }),
    )
    threads.delete(id)
    chats.value = chats.value.filter((chat) => chat.id !== id)
  }

  return { chats, nextCursor, listing, threads, list, more, open, start, ask, stop, rename, remove }
})
