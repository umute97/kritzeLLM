import { createParser } from 'eventsource-parser'

import { api, call, isAbort } from './client'
import { ApiError } from './errors'
import type { ChatStreamEvent, Message, Problem } from './types'

/** The stream ended before the answer was saved: the connection dropped halfway. */
export class BrokenStreamError extends Error {
  constructor(options?: ErrorOptions) {
    super('The answer stream broke off', options)
    this.name = 'BrokenStreamError'
  }
}

/**
 * Asks a question and streams the answer, handing every event to `onEvent` as it arrives.
 * Resolves with the saved answer. Rejects with an `ApiError` when the question is turned down or
 * the answer fails (an `error` event), with a `BrokenStreamError` when the stream stops before
 * the answer is saved, and with the abort when `signal` calls it off.
 */
export async function streamAnswer(
  conversationId: string,
  question: string,
  { signal, onEvent }: { signal?: AbortSignal; onEvent: (event: ChatStreamEvent) => void },
): Promise<Message> {
  const body = await call(
    api.POST('/conversations/{conversationId}/messages', {
      params: { path: { conversationId } },
      body: { content: question },
      headers: { Accept: 'text/event-stream' },
      parseAs: 'stream',
      signal,
    }),
  )
  if (!body) throw new BrokenStreamError()

  let saved: Message | undefined
  let problem: Problem | undefined
  const parser = createParser({
    onEvent({ data }) {
      const event = JSON.parse(data) as ChatStreamEvent
      if (event.type === 'messageEnd') saved = event.message
      else if (event.type === 'error') problem = event.problem
      onEvent(event)
    },
  })

  const reader = body.getReader()
  const decoder = new TextDecoder()
  try {
    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      parser.feed(decoder.decode(value, { stream: true }))
    }
  } catch (cause) {
    if (isAbort(cause)) throw cause
    signal?.throwIfAborted()
    throw new BrokenStreamError({ cause })
  }
  if (problem) throw new ApiError(problem)
  if (!saved) throw new BrokenStreamError()
  return saved
}
