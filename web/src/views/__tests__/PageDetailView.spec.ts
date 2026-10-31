import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia, type Pinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { createMemoryHistory, createRouter, RouterLink, RouterView } from 'vue-router'

import type { Block, Page, PageDetail } from '@/api/types'
import { setLocale, uiMessages } from '@/i18n'
import { json, makeBlock, makeJournal, makePage } from '@/test-utils'
import { createCottage, useToasts } from '@/ui'
import PageDetailView from '@/views/PageDetailView.vue'

type Handler = (request: Request) => Response | Promise<Response>

const journal = makeJournal({ id: 'jrn_1', pageCount: 3 })
let pinia: Pinia
let wrapper: VueWrapper | undefined

beforeEach(() => {
  pinia = createPinia()
  setActivePinia(pinia)
})

afterEach(() => {
  wrapper?.unmount()
  wrapper = undefined
  useToasts().clear()
  vi.useRealTimers()
  vi.unstubAllGlobals()
  setLocale('en')
})

function detailOf(page: Page, blocks: Block[] = []): PageDetail {
  return { ...page, blocks: blocks.map((b) => ({ ...b, pageId: page.id })) }
}

/** Answers API calls by "METHOD /path"; the journal and its page list are always there. */
function serve(pages: PageDetail[], handlers: Record<string, Handler> = {}) {
  const fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const request =
      input instanceof Request ? input : new Request(new URL(String(input), location.origin), init)
    const key = `${request.method} ${new URL(request.url).pathname}`
    const handler = handlers[key]
    if (handler) return handler(request)
    if (key === `GET /api/v1/journals/${journal.id}`) return json(journal)
    if (key === 'GET /api/v1/pages') return json({ items: pages, nextCursor: null })
    const page = pages.find((p) => key === `GET /api/v1/pages/${p.id}`)
    if (page) return json(page)
    return json({ type: 'about:blank', title: 'Not Found', status: 404 }, 404)
  })
  vi.stubGlobal('fetch', fetch)
  return fetch
}

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((r) => (resolve = r))
  return { promise, resolve }
}

const Shelf = defineComponent({ render: () => h('p', 'The shelf') })

async function open(pageId: string) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'library', component: Shelf },
      { path: '/journals/:journalId', name: 'journal', component: Shelf },
      { path: '/pages/:pageId', name: 'page', component: PageDetailView, props: true },
    ],
  })
  await router.push(`/pages/${pageId}`)
  wrapper = mount(defineComponent({ render: () => h(RouterView) }), {
    attachTo: document.body,
    global: { plugins: [pinia, router, createCottage({ link: RouterLink, messages: uiMessages })] },
  })
  await flushPromises()
  return { wrapper, router }
}

function button(view: VueWrapper, label: string) {
  const found = view.findAll('button').find((b) => b.text() === label)
  if (!found) throw new Error(`No button "${label}"`)
  return found
}

const toastTitles = () => useToasts().items.value.map((t) => t.title)

describe('the page detail view', () => {
  it('loads the page and shows one card per block, in reading order', async () => {
    const page = detailOf(makePage({ id: 'pg_a', pageNumber: 7 }), [
      makeBlock({ seq: 0, kind: 'heading', text: 'Sunday' }),
      makeBlock({ seq: 1, text: 'Picked wild garlic by the river.' }),
    ])
    serve([page])
    const { wrapper } = await open('pg_a')

    expect(wrapper.find('h1').text()).toBe('Page 7')
    expect(wrapper.text()).toContain('Green notebook')
    expect(wrapper.findAll('textarea').map((t) => t.element.value)).toEqual([
      'Sunday',
      'Picked wild garlic by the river.',
    ])
  })

  it('speaks German, the cottage library included, after switching', async () => {
    const page = detailOf(makePage({ id: 'pg_a', pageNumber: 7 }), [
      makeBlock({ seq: 0, uncertain: true }),
    ])
    serve([page])
    const { wrapper } = await open('pg_a')

    setLocale('de')
    await flushPromises()

    expect(wrapper.find('h1').text()).toBe('Seite 7')
    expect(wrapper.text()).toContain('1 Block')
    expect(button(wrapper, 'Passt so').exists()).toBe(true)
  })

  it('shows "This page wandered off" on a 404', async () => {
    serve([])
    const { wrapper } = await open('pg_gone')

    expect(wrapper.text()).toContain('This page wandered off')
  })

  it('shows the failed banner with the page’s error', async () => {
    const error = { type: 'about:blank', title: 'Model error', status: 502, detail: 'Timed out.' }
    serve([detailOf(makePage({ id: 'pg_a', status: 'failed', error }))])
    const { wrapper } = await open('pg_a')

    expect(wrapper.text()).toContain('We couldn’t read this page')
    expect(wrapper.text()).toContain('Timed out.')
  })

  it('shows "Still reading" instead of blocks while transcribing', async () => {
    vi.useFakeTimers({ toFake: ['setInterval'] })
    serve([detailOf(makePage({ id: 'pg_a', status: 'transcribing' }), [makeBlock()])])
    const { wrapper } = await open('pg_a')

    expect(wrapper.text()).toContain('Still reading this page')
    expect(wrapper.find('textarea').exists()).toBe(false)
  })

  it('saves an edit with PATCH /blocks/{id} and shows "saved"', async () => {
    const block = makeBlock({ text: 'Picked wild garlc' })
    const page = detailOf(makePage({ id: 'pg_a' }), [block])
    const sent: unknown[] = []
    serve([page], {
      [`PATCH /api/v1/blocks/${block.id}`]: async (request) => {
        const body = (await request.json()) as { text: string }
        sent.push(body)
        return json({ block: { ...page.blocks[0], text: body.text }, job: {} })
      },
    })
    const { wrapper } = await open('pg_a')

    await wrapper.find('textarea').setValue('Picked wild garlic')
    expect(wrapper.text()).toContain('changed, not saved')
    await button(wrapper, 'Save').trigger('click')
    await flushPromises()

    expect(sent).toEqual([{ text: 'Picked wild garlic' }])
    expect(wrapper.text()).not.toContain('changed, not saved')
    expect(wrapper.text()).toContain('saved')
  })

  it('keeps text typed while a save is still running', async () => {
    const block = makeBlock({ text: 'Picked wild garlc' })
    const page = detailOf(makePage({ id: 'pg_a' }), [block])
    const answer = deferred<Response>()
    serve([page], { [`PATCH /api/v1/blocks/${block.id}`]: () => answer.promise })
    const { wrapper } = await open('pg_a')

    const field = wrapper.find('textarea')
    await field.setValue('Picked wild garlic')
    await button(wrapper, 'Save').trigger('click')
    await field.setValue('Picked wild garlic, lots of it')
    answer.resolve(json({ block: { ...page.blocks[0], text: 'Picked wild garlic' }, job: {} }))
    await flushPromises()

    expect(field.element.value).toBe('Picked wild garlic, lots of it')
    expect(wrapper.text()).toContain('changed, not saved')
  })

  it('warns when saving during a reading (409)', async () => {
    const block = makeBlock()
    serve([detailOf(makePage({ id: 'pg_a' }), [block])], {
      [`PATCH /api/v1/blocks/${block.id}`]: () =>
        json({ type: 'about:blank', title: 'Page busy', status: 409 }, 409),
    })
    const { wrapper } = await open('pg_a')

    await wrapper.find('textarea').setValue('Something else')
    await button(wrapper, 'Save').trigger('click')
    await flushPromises()

    const toast = useToasts().items.value.at(-1)
    expect(toast).toMatchObject({ tone: 'warning', title: 'Couldn’t save block 1' })
    expect(wrapper.text()).toContain('changed, not saved')
  })

  it('“Looks right” sends { uncertain: false }', async () => {
    const block = makeBlock({ text: 'Met [?] at the market', uncertain: true })
    const page = detailOf(makePage({ id: 'pg_a' }), [block])
    const sent: unknown[] = []
    serve([page], {
      [`PATCH /api/v1/blocks/${block.id}`]: async (request) => {
        sent.push(await request.json())
        return json({ block: { ...page.blocks[0], uncertain: false }, job: {} })
      },
    })
    const { wrapper } = await open('pg_a')

    await button(wrapper, 'Looks right').trigger('click')
    await flushPromises()

    expect(sent).toEqual([{ uncertain: false }])
    expect(wrapper.findAll('button').some((b) => b.text() === 'Looks right')).toBe(false)
  })

  it('won’t save an empty block', async () => {
    const block = makeBlock()
    const fetch = serve([detailOf(makePage({ id: 'pg_a' }), [block])])
    const { wrapper } = await open('pg_a')

    await wrapper.find('textarea').setValue('  \n ')
    await button(wrapper, 'Save').trigger('click')
    await flushPromises()

    expect(toastTitles()).toContain('A block can’t be empty')
    const patched = fetch.mock.calls.some(
      ([request]) => request instanceof Request && request.method === 'PATCH',
    )
    expect(patched).toBe(false)
  })

  it('asks before leaving with unsaved changes, and stays on the page when you cancel', async () => {
    serve([detailOf(makePage({ id: 'pg_a' }), [makeBlock()])])
    const { wrapper, router } = await open('pg_a')

    await wrapper.find('textarea').setValue('Half a thought')
    await router.push('/')
    await flushPromises()

    expect(wrapper.text()).toContain('Leave without saving?')
    expect(wrapper.text()).toContain('Your changes to 1 block will be lost.')
    await button(wrapper, 'Keep it').trigger('click')
    expect(router.currentRoute.value.name).toBe('page')
    expect(wrapper.find('textarea').element.value).toBe('Half a thought')

    await router.push('/')
    await flushPromises()
    await button(wrapper, 'Leave anyway').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.name).toBe('library')
  })

  it('shows the newest page when you page quickly', async () => {
    const pages = [1, 2, 3].map((n) =>
      detailOf(makePage({ id: `pg_${n}`, pageNumber: n }), [makeBlock({ text: `Page ${n} text` })]),
    )
    const slow = deferred<Response>()
    serve(pages, { 'GET /api/v1/pages/pg_2': () => slow.promise })
    const { wrapper, router } = await open('pg_1')

    void router.push('/pages/pg_2')
    await flushPromises()
    await router.push('/pages/pg_3')
    await flushPromises()
    slow.resolve(json(pages[1]))
    await flushPromises()

    expect(wrapper.find('h1').text()).toBe('Page 3')
    expect(wrapper.find('textarea').element.value).toBe('Page 3 text')
  })
})
