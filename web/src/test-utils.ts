// Small builders for tests: API objects with sensible defaults, and JSON responses.
import type { Block, ChatStreamEvent, Journal, Message, Page, Source } from '@/api/types'

let counter = 0

/** A TypeID-shaped id, unique per call. */
export function typeId(prefix: string): string {
  counter++
  return `${prefix}_01${String(counter).padStart(24, '0')}`
}

export function makeJournal(overrides: Partial<Journal> = {}): Journal {
  return {
    id: typeId('jrn'),
    name: 'Green notebook',
    description: null,
    pageCount: 0,
    createdAt: '2026-03-01T10:00:00Z',
    updatedAt: '2026-03-01T10:00:00Z',
    ...overrides,
  }
}

export function makePage(overrides: Partial<Page> = {}): Page {
  const id = overrides.id ?? typeId('pg')
  return {
    id,
    journalId: 'jrn_1',
    pageNumber: 1,
    pageLabel: null,
    entryDates: [],
    status: 'ready',
    error: null,
    image: {
      width: 1500,
      height: 2000,
      urls: {
        original: `/api/v1/pages/${id}/image?variant=original`,
        normalized: `/api/v1/pages/${id}/image?variant=normalized`,
        thumbnail: `/api/v1/pages/${id}/image?variant=thumbnail`,
      },
    },
    transcriptionModel: null,
    createdAt: '2026-03-03T10:00:00Z',
    updatedAt: '2026-03-03T10:00:00Z',
    ...overrides,
  }
}

export function makeBlock(overrides: Partial<Block> = {}): Block {
  return {
    id: typeId('blk'),
    pageId: 'pg_1',
    seq: 0,
    kind: 'paragraph',
    text: 'Picked wild garlic by the river.',
    uncertain: false,
    ...overrides,
  }
}

export function makeSource(overrides: Partial<Source> = {}): Source {
  return {
    ref: 1,
    blockId: typeId('blk'),
    pageId: typeId('pg'),
    journalId: 'jrn_1',
    pageNumber: 12,
    entryDates: ['2026-03-03'],
    quote: 'I finally planted the sweet peas by the fence.',
    ...overrides,
  }
}

export function makeMessage(overrides: Partial<Message> = {}): Message {
  return {
    id: typeId('msg'),
    role: 'assistant',
    content: 'You planted them by the fence [1].',
    toolCalls: [],
    sources: [],
    createdAt: '2026-03-03T10:00:00Z',
    ...overrides,
  }
}

/** A server-sent events answer to feed by hand: `send` events, then `end` or `fail` it. */
export function eventStream() {
  const encoder = new TextEncoder()
  let controller!: ReadableStreamDefaultController<Uint8Array>
  const body = new ReadableStream<Uint8Array>({ start: (c) => (controller = c) })
  return {
    response: () => new Response(body, { headers: { 'Content-Type': 'text/event-stream' } }),
    send(...events: ChatStreamEvent[]) {
      for (const event of events)
        this.raw(`event: ${event.type}\ndata: ${JSON.stringify(event)}\n\n`)
    },
    raw: (chunk: string | Uint8Array) =>
      controller.enqueue(typeof chunk === 'string' ? encoder.encode(chunk) : chunk),
    end: () => controller.close(),
    fail: (error: unknown) => controller.error(error),
  }
}

export function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': status >= 400 ? 'application/problem+json' : 'application/json' },
  })
}

/** The URL of the n-th call to a stubbed fetch, without the origin. */
export function calledUrl(fetch: { mock: { calls: unknown[][] } }, n = 0): string {
  const request = fetch.mock.calls[n]?.[0]
  const url = request instanceof Request ? request.url : String(request)
  return url.replace(/^https?:\/\/[^/]+/, '')
}
