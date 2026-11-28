import { flushPromises, type VueWrapper } from '@vue/test-utils'
import { beforeEach, describe, expect, it } from 'vitest'

import type { SearchHit } from '@/api/types'
import {
  button,
  Elsewhere,
  json,
  makeBlock,
  makeJournal,
  makePage,
  mountRoute,
  notFound,
  problem,
  stubFetch,
} from '@/test-utils'
import { useToasts } from '@/ui'
import SearchView from '@/views/SearchView.vue'

const garden = makeJournal({ id: 'jrn_garden', name: 'Green notebook' })
const travel = makeJournal({ id: 'jrn_travel', name: 'Travel journal' })

beforeEach(() => {
  localStorage.clear()
})

function hit(overrides: Partial<SearchHit> = {}): SearchHit {
  const page = makePage({ journalId: garden.id, pageNumber: 12, entryDates: ['2026-03-03'] })
  return {
    page,
    blocks: [
      makeBlock({ pageId: page.id, seq: 1, text: 'I finally planted the sweet peas.' }),
      makeBlock({ pageId: page.id, seq: 2, kind: 'list', text: 'basil, marigolds' }),
    ],
    score: 2 / 61,
    vectorRank: 1,
    keywordRank: 1,
    ...overrides,
  }
}

/** Answers the journals list, and every search with `search(params)`. */
function serve(search: (params: URLSearchParams) => Response = () => json({ items: [hit()] })) {
  return stubFetch((request) => {
    const url = new URL(request.url)
    if (url.pathname === '/api/v1/journals') {
      return json({ items: [garden, travel], nextCursor: null })
    }
    if (url.pathname === '/api/v1/search') return search(url.searchParams)
    return notFound()
  })
}

/** The query of every search asked so far. */
function searches(fetch: ReturnType<typeof serve>): Record<string, string>[] {
  return fetch.mock.calls
    .map(
      ([input]) => new URL(input instanceof Request ? input.url : String(input), location.origin),
    )
    .filter((url) => url.pathname === '/api/v1/search')
    .map((url) => Object.fromEntries(url.searchParams))
}

function open(path = '/search') {
  return mountRoute(
    [
      { path: '/', name: 'library', component: Elsewhere },
      { path: '/search', name: 'search', component: SearchView },
      { path: '/pages/:pageId', name: 'page', component: Elsewhere },
    ],
    path,
  )
}

async function searchFor(view: VueWrapper, text: string) {
  await view.get('input[type="search"]').setValue(text)
  await view.get('form[role="search"]').trigger('submit')
  await flushPromises()
}

function field(view: VueWrapper, label: string) {
  const found = view.findAll('label').find((l) => l.text() === label)
  if (!found) throw new Error(`No field "${label}"`)
  return view.get(`[id="${found.attributes('for')}"]`)
}

describe('the search view', () => {
  it('searches from the field, keeps the search in the URL, and links hits to their page', async () => {
    const found = hit()
    const fetch = serve(() => json({ items: [found] }))
    const { wrapper, router } = await open()
    expect(wrapper.text()).toContain('What are you looking for?')

    await searchFor(wrapper, '  sweet peas ')

    expect(router.currentRoute.value.fullPath).toBe('/search?q=sweet+peas')
    expect(searches(fetch)).toEqual([{ q: 'sweet peas', mode: 'hybrid', limit: '20' }])
    expect(wrapper.text()).toContain('2 blocks on 1 page')
    expect(wrapper.text()).toContain('Green notebook')
    expect(new Set(wrapper.findAll('mark').map((m) => m.text()))).toEqual(
      new Set(['sweet', 'peas']),
    )
    const link = wrapper.get('ol a')
    const blocks = found.blocks.map((block) => block.id).join(',')
    expect(link.attributes('href')).toBe(`/pages/${found.page.id}?blocks=${blocks}`)
    expect(link.text()).toContain('Page 12')
    expect(wrapper.find('[role="meter"]').exists()).toBe(false)
  })

  it('opens with the search the URL holds, filters included', async () => {
    const fetch = serve()
    const { wrapper } = await open(
      `/search?q=Oma&journalId=${travel.id}&dateFrom=2026-01-01&dateTo=2026-03-31`,
    )

    expect(searches(fetch)).toEqual([
      {
        q: 'Oma',
        mode: 'hybrid',
        journalId: travel.id,
        dateFrom: '2026-01-01',
        dateTo: '2026-03-31',
        limit: '20',
      },
    ])
    expect(wrapper.get<HTMLInputElement>('input[type="search"]').element.value).toBe('Oma')
    expect(wrapper.get('select').element.value).toBe(travel.id)
    const [from, to] = wrapper.findAll<HTMLInputElement>('input[type="date"]')
    expect([from!.element.value, to!.element.value]).toEqual(['2026-01-01', '2026-03-31'])
    expect(from!.attributes('max')).toBe('2026-03-31')
  })

  it('searches again when a filter changes', async () => {
    const fetch = serve()
    const { wrapper, router } = await open('/search?q=Oma')

    await wrapper.get('select').setValue(garden.id)
    await flushPromises()

    expect(router.currentRoute.value.query).toEqual({ q: 'Oma', journalId: garden.id })
    expect(searches(fetch).at(-1)).toMatchObject({ q: 'Oma', journalId: garden.id })
  })

  it('sorts by words or meaning with a new search, and by date without one', async () => {
    const march = hit({ page: makePage({ journalId: garden.id, entryDates: ['2026-03-03'] }) })
    const undated = hit({ page: makePage({ journalId: garden.id, entryDates: [] }) })
    const june = hit({ page: makePage({ journalId: garden.id, entryDates: ['2026-06-02'] }) })
    const fetch = serve(() => json({ items: [march, undated, june] }))
    const { wrapper, router } = await open('/search?q=sweet+peas')
    const shown = () => wrapper.findAll('ol a').map((a) => a.attributes('href')!.split('?')[0])
    const pages = (...hits: SearchHit[]) => hits.map((h) => `/pages/${h.page.id}`)

    expect(shown()).toEqual(pages(march, undated, june))
    expect(wrapper.text()).not.toContain('sorted by')

    await field(wrapper, 'Sort').setValue('words')
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ q: 'sweet peas', sort: 'words' })
    expect(searches(fetch).at(-1)).toMatchObject({ mode: 'keyword' })
    expect(wrapper.text()).toContain('3 pages, sorted by words')

    await field(wrapper, 'Sort').setValue('date')
    await flushPromises()
    expect(searches(fetch).at(-1)).toMatchObject({ mode: 'hybrid' })
    expect(shown()).toEqual(pages(june, march, undated))
    expect(wrapper.text()).toContain('3 pages, newest first')

    const asked = searches(fetch).length
    await field(wrapper, 'Sort').setValue('relevance')
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ q: 'sweet peas' })
    expect(searches(fetch)).toHaveLength(asked)
    expect(shown()).toEqual(pages(march, undated, june))
  })

  it('opens sorted by meaning from the URL', async () => {
    const fetch = serve()
    const { wrapper } = await open('/search?q=sweet+peas&sort=meaning')

    expect(searches(fetch)).toEqual([{ q: 'sweet peas', mode: 'vector', limit: '20' }])
    expect(field(wrapper, 'Sort').element).toHaveProperty('value', 'meaning')
  })

  it('offers to search everywhere when a filtered search finds nothing', async () => {
    const fetch = serve((params) => json({ items: params.has('journalId') ? [] : [hit()] }))
    const { wrapper, router } = await open(`/search?q=otters&journalId=${garden.id}`)

    expect(wrapper.text()).toContain('No pages mention “otters”')
    await button(wrapper, 'Search all journals').trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.query).toEqual({ q: 'otters' })
    expect(searches(fetch).at(-1)).toEqual({ q: 'otters', mode: 'hybrid', limit: '20' })
    expect(wrapper.find('ol a').exists()).toBe(true)
  })

  it('remembers recent searches on this device, newest first, and runs them again', async () => {
    const fetch = serve()
    const { wrapper } = await open()

    await searchFor(wrapper, 'sweet peas')
    await searchFor(wrapper, 'grandma’s cake')
    await searchFor(wrapper, 'Sweet Peas')

    expect(JSON.parse(localStorage.getItem('kritzellm.recentSearches')!)).toEqual([
      'Sweet Peas',
      'grandma’s cake',
    ])
    await button(wrapper, 'grandma’s cake').trigger('click')
    await flushPromises()

    expect(searches(fetch).at(-1)).toMatchObject({ q: 'grandma’s cake' })
  })

  it('says words still work when meaning search can’t reach its model', async () => {
    const fetch = serve((params) =>
      params.get('mode') === 'keyword' ? json({ items: [hit()] }) : json(problem(502), 502),
    )
    const { wrapper } = await open('/search?q=sweet+peas')

    const [toast] = useToasts().items.value
    expect(toast).toMatchObject({ tone: 'warning', title: 'Couldn’t search your pages' })
    toast!.action!.run()
    await flushPromises()

    expect(searches(fetch).at(-1)).toMatchObject({ mode: 'keyword' })
    expect(wrapper.find('ol a').exists()).toBe(true)
  })
})
