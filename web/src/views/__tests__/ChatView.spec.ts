import { flushPromises, type VueWrapper } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import type { Conversation, ConversationDetail, Message } from '@/api/types'
import {
  button,
  Elsewhere,
  eventStream,
  json,
  makeJournal,
  makeMessage,
  makeSource,
  mountRoute,
  problem,
  stubFetch,
  typeId,
} from '@/test-utils'
import ChatView from '@/views/ChatView.vue'

function chat(overrides: Partial<ConversationDetail> = {}): ConversationDetail {
  const now = new Date().toISOString()
  return {
    id: typeId('cnv'),
    title: null,
    createdAt: now,
    updatedAt: now,
    messages: [],
    ...overrides,
  }
}

function summary({ id, title, createdAt, updatedAt }: ConversationDetail): Conversation {
  return { id, title, createdAt, updatedAt }
}

function question(content: string): Message {
  return makeMessage({ role: 'user', content, sources: [] })
}

type Answer = (request: Request) => Response

/** An answer streamed from `stream`, broken off the way a browser does when it's stopped. */
function streamed(stream: ReturnType<typeof eventStream>): Answer {
  return (request) => {
    request.signal.addEventListener('abort', () =>
      stream.fail(new DOMException('The operation was aborted.', 'AbortError')),
    )
    return stream.response()
  }
}

/** A tiny API: chats kept in `chats`, each question answered by the next of `answers`. */
function serve() {
  const server = {
    chats: new Map<string, ConversationDetail>(),
    nextCursor: null as string | null,
    older: [] as ConversationDetail[],
    answers: [] as Answer[],
    asked: [] as { id: string; content: string }[],
    renamed: [] as unknown[],
    deleted: [] as string[],
    add(detail: ConversationDetail) {
      server.chats.set(detail.id, detail)
      return detail
    },
  }
  stubFetch(async (request) => {
    const url = new URL(request.url)
    const path = url.pathname.replace('/api/v1', '')
    if (path === '/journals') return json({ items: [makeJournal()], nextCursor: null })
    if (path === '/conversations' && request.method === 'GET') {
      const older = url.searchParams.has('cursor')
      const items = older ? server.older : [...server.chats.values()]
      return json({ items: items.map(summary), nextCursor: older ? null : server.nextCursor })
    }
    if (path === '/conversations' && request.method === 'POST') {
      return json(summary(server.add(chat())), 201)
    }
    const [, id, messages] = path.match(/^\/conversations\/([^/]+)(\/messages)?$/) ?? []
    const found = id ? server.chats.get(id) : undefined
    if (!id || !found) return json(problem(404, 'Not Found', 'No such chat.'), 404)
    if (messages) {
      server.asked.push({ id, content: ((await request.json()) as { content: string }).content })
      return server.answers.shift()!(request)
    }
    if (request.method === 'PATCH') {
      const body = (await request.json()) as { title: string | null }
      server.renamed.push(body)
      found.title = body.title
      return json(summary(found))
    }
    if (request.method === 'DELETE') {
      server.deleted.push(id)
      server.chats.delete(id)
      return new Response(null, { status: 204 })
    }
    return json(found)
  })
  return server
}

function open(path: string) {
  return mountRoute(
    [
      { path: '/chat/:conversationId?', name: 'chat', component: ChatView, props: true },
      { path: '/pages/:pageId', name: 'page', component: Elsewhere },
    ],
    path,
  )
}

async function ask(view: VueWrapper, text: string) {
  const box = view.get('textarea')
  await box.setValue(text)
  await box.trigger('keydown', { key: 'Enter' })
  await flushPromises()
}

const chips = (view: VueWrapper) => view.findAll('button[aria-pressed]').map((chip) => chip.text())

describe('the chat view', () => {
  it('starts a chat with its first question and streams the answer into it', async () => {
    const server = serve()
    const stream = eventStream()
    server.answers.push(streamed(stream))
    const { wrapper, router } = await open('/chat')
    expect(wrapper.get('h1').text()).toBe('New chat')
    expect(wrapper.text()).toContain('Ask your journal anything')
    expect(wrapper.text()).toContain('Who did I spend time with this month?')

    await ask(wrapper, '  Where did I plant the sweet peas? ')

    const [created] = server.chats.keys()
    expect(router.currentRoute.value.fullPath).toBe(`/chat/${created}`)
    expect(server.asked).toEqual([{ id: created, content: 'Where did I plant the sweet peas?' }])
    expect(wrapper.get('textarea').element.value).toBe('')
    stream.send({ type: 'messageStart' })
    await flushPromises()
    expect(wrapper.text()).toContain('flipping pages…')
    expect(button(wrapper, 'Stop').exists()).toBe(true)

    stream.send({
      type: 'toolCall',
      id: 'call-1',
      name: 'search_journal',
      args: { query: 'sweet peas' },
    })
    await flushPromises()
    expect(wrapper.text()).toContain('looking through your journal for “sweet peas”…')

    stream.send(
      { type: 'toolResult', id: 'call-1', name: 'search_journal', pages: 2 },
      { type: 'textDelta', text: 'By the fence [1]' },
    )
    await flushPromises()
    expect(wrapper.text()).toContain('By the fence')
    expect(wrapper.get('button[aria-pressed]').attributes('disabled')).toBeDefined()

    // Saved: the server now has both messages and a title from the question.
    const source = makeSource({ pageNumber: 12 })
    const saved = makeMessage({
      content: 'By the fence [1].',
      sources: [source],
      toolCalls: [{ name: 'search_journal', args: { query: 'sweet peas' }, pages: 2 }],
    })
    Object.assign(server.chats.get(created!)!, {
      title: 'Where did I plant the sweet peas?',
      messages: [question('Where did I plant the sweet peas?'), saved],
    })
    stream.send({ type: 'source', source }, { type: 'messageEnd', message: saved })
    stream.end()
    await flushPromises()

    const chip = wrapper.get('button[aria-pressed]')
    expect(chip.text()).toBe('p. 12')
    expect(chip.attributes('disabled')).toBeUndefined()
    expect(wrapper.get('h1').text()).toBe('Where did I plant the sweet peas?')
    expect(wrapper.get('nav[aria-label="Earlier chats"]').text()).toContain(
      'Where did I plant the sweet peas?',
    )
    expect(wrapper.text()).toContain(source.quote)
    expect(wrapper.find('button[aria-label="Send"]').exists()).toBe(true)

    // What the helper did is a footnote in the answer now.
    const footnote = button(wrapper, 'Searched once')
    await footnote.trigger('click')
    expect(wrapper.get(`#${footnote.attributes('aria-controls')}`).text()).toBe(
      'Looked for “sweet peas”: 2 pages',
    )
  })

  it('picks the sources a chip cites, which open their page with the block highlighted', async () => {
    const server = serve()
    const fence = makeSource({ ref: 1, pageNumber: 12, quote: 'Planted the sweet peas.' })
    const twine = makeSource({
      ref: 2,
      pageId: fence.pageId,
      pageNumber: 12,
      quote: 'Bought twine.',
    })
    const shoots = makeSource({ ref: 3, pageNumber: 14, quote: 'First little shoots!' })
    const bloom = makeSource({ ref: 1, pageNumber: 20, quote: 'They bloomed.' })
    const searched = { name: 'search_journal', args: { query: 'sweet peas' }, pages: 2 }
    const first = makeMessage({
      content: 'By the fence [1][2], and they came up soon [3].',
      sources: [fence, twine, shoots],
      toolCalls: [
        searched,
        { ...searched, name: 'find_exact', args: { text: 'peas' } },
        { name: 'read_page', args: {}, pages: 1 },
      ],
    })
    const second = makeMessage({ content: 'They bloomed in May [1].', sources: [bloom] })
    const garden = server.add(
      chat({
        title: 'Sweet peas',
        messages: [question('Where?'), first, question('Bloom?'), second],
      }),
    )
    const { wrapper } = await open(`/chat/${garden.id}`)

    // Sources follows the latest answer until a chip is picked.
    const panel = () => wrapper.findAll('section').at(-1)!
    expect(panel().text()).toContain('They bloomed.')
    expect(chips(wrapper)).toEqual(['p. 12', 'p. 14', 'p. 20'])

    await button(wrapper, 'p. 12').trigger('click')

    expect(button(wrapper, 'p. 12').attributes('aria-pressed')).toBe('true')
    const cards = panel().findAll('li[data-ref]')
    expect(cards.map((card) => card.text())).toEqual([
      expect.stringContaining('Planted the sweet peas.'),
      expect.stringContaining('Bought twine.'),
      expect.stringContaining('First little shoots!'),
    ])
    const lifted = cards.map((card) => card.get('div').classes().includes('shadow-soft'))
    expect(lifted).toEqual([true, true, false])
    expect(cards[0]!.get('a').attributes('href')).toBe(
      `/pages/${fence.pageId}?blocks=${fence.blockId}`,
    )
    expect(cards[0]!.text()).toContain('Page 12')

    // What the helper did is a footnote that unfolds into its steps.
    const footnote = button(wrapper, 'Searched twice · read 1 page')
    expect(footnote.attributes('aria-expanded')).toBe('false')
    await footnote.trigger('click')
    expect(wrapper.get(`#${footnote.attributes('aria-controls')}`).text()).toBe(
      'Looked for “sweet peas”: 2 pagesLooked for “peas” word for word: 2 pagesRead a page',
    )
  })

  it('keeps what arrived when you stop, saves nothing, and can ask again', async () => {
    const server = serve()
    const stream = eventStream()
    server.answers.push(streamed(stream))
    const garden = server.add(chat())
    const { wrapper } = await open(`/chat/${garden.id}`)
    await ask(wrapper, 'Sweet peas?')
    stream.send({ type: 'textDelta', text: 'You planted them by [1]' })
    await flushPromises()

    await button(wrapper, 'Stop').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('You planted them by')
    expect(wrapper.text()).toContain('You stopped this answer, so it wasn’t kept.')
    expect(wrapper.find('button[aria-label="Send"]').exists()).toBe(true)

    const again = eventStream()
    server.answers.push(streamed(again))
    await button(wrapper, 'Ask again').trigger('click')
    await flushPromises()
    expect(server.asked.map((asked) => asked.content)).toEqual(['Sweet peas?', 'Sweet peas?'])
    expect(wrapper.text()).not.toContain('You stopped this answer')
  })

  it('says why an answer failed, keeps what arrived, and offers to ask again', async () => {
    const server = serve()
    const failing = eventStream()
    const breaking = eventStream()
    server.answers.push(streamed(failing), streamed(breaking))
    const garden = server.add(chat())
    const { wrapper } = await open(`/chat/${garden.id}`)

    await ask(wrapper, 'Sweet peas?')
    failing.send(
      { type: 'textDelta', text: 'You planted' },
      {
        type: 'error',
        problem: problem(502, 'Bad Gateway', 'The chat model couldn’t answer. Try again later.'),
      },
    )
    failing.end()
    await flushPromises()

    expect(wrapper.text()).toContain('You planted')
    expect(wrapper.get('[role="alert"]').text()).toContain('The chat model couldn’t answer.')

    await button(wrapper, 'Ask again').trigger('click')
    breaking.send({ type: 'textDelta', text: 'You' })
    breaking.end()
    await flushPromises()
    expect(wrapper.get('[role="alert"]').text()).toContain('The answer stopped halfway.')
  })

  it('offers a new chat for a question a full one turns down', async () => {
    const server = serve()
    const full = server.add(chat({ title: 'Long chat' }))
    const stream = eventStream()
    server.answers.push(
      () => json(problem(409, 'Conflict', 'This conversation is full.'), 409),
      streamed(stream),
    )
    const { wrapper, router } = await open(`/chat/${full.id}`)

    await ask(wrapper, 'One more?')
    expect(wrapper.text()).toContain('This chat is full')

    await button(wrapper, 'Ask in a new chat').trigger('click')
    await flushPromises()

    const fresh = [...server.chats.keys()].find((id) => id !== full.id)!
    expect(server.asked).toEqual([
      { id: full.id, content: 'One more?' },
      { id: fresh, content: 'One more?' },
    ])
    expect(router.currentRoute.value.fullPath).toBe(`/chat/${fresh}`)
    router.back()
    await flushPromises()
    expect(router.currentRoute.value.fullPath).toBe(`/chat/${full.id}`)
  })

  it('says so when a chat isn’t there', async () => {
    serve()
    const { wrapper } = await open('/chat/cnv_01000000000000000000000000')
    expect(wrapper.text()).toContain('This chat isn’t here')
  })

  it('renames and deletes the open chat', async () => {
    const server = serve()
    const garden = server.add(chat({ title: 'Sweet peas' }))
    const { wrapper, router } = await open(`/chat/${garden.id}`)

    await wrapper.get('button[aria-label="Chat actions"]').trigger('click')
    await button(wrapper, 'Rename').trigger('click')
    const name = wrapper.get('dialog input')
    expect((name.element as HTMLInputElement).value).toBe('Sweet peas')
    await name.setValue('  Garden ')
    await wrapper.get('dialog form').trigger('submit')
    await flushPromises()

    expect(server.renamed).toEqual([{ title: 'Garden' }])
    expect(wrapper.get('h1').text()).toBe('Garden')
    expect(wrapper.get('nav[aria-label="Earlier chats"]').text()).toContain('Garden')

    await wrapper.get('button[aria-label="Chat actions"]').trigger('click')
    await button(wrapper, 'Delete chat').trigger('click')
    const confirm = wrapper.findAll('dialog[open] button').find((b) => b.text() === 'Delete chat')!
    await confirm.trigger('click')
    await flushPromises()

    expect(server.deleted).toEqual([garden.id])
    expect(router.currentRoute.value.fullPath).toBe('/chat')
    expect(wrapper.get('nav[aria-label="Earlier chats"]').text()).not.toContain('Garden')
  })

  it('lists earlier chats, most recent first, and older ones on request', async () => {
    const server = serve()
    const garden = server.add(chat({ title: 'Sweet peas' }))
    server.add(chat())
    server.nextCursor = 'cnv_01000000000000000000000000.1'
    server.older = [chat({ title: 'Dreams about the sea', updatedAt: '2025-10-02T10:00:00Z' })]
    const { wrapper } = await open(`/chat/${garden.id}`)

    const list = () => wrapper.get('nav[aria-label="Earlier chats"]')
    expect(
      list()
        .findAll('li')
        .map((item) => item.text()),
    ).toEqual(['Sweet peastoday', 'New chattoday'])
    expect(list().get('a[aria-current="page"]').text()).toContain('Sweet peas')

    await button(wrapper, 'Show older chats').trigger('click')
    await flushPromises()

    expect(list().findAll('li').at(-1)!.text()).toBe('Dreams about the seaOct 2, 2025')
    expect(list().text()).not.toContain('Show older chats')
  })
})
