import { flushPromises, type VueWrapper } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { Journal, Page } from '@/api/types'
import { uploadPage } from '@/api/upload'
import {
  button,
  Elsewhere,
  json,
  makeJournal,
  makePage,
  mountRoute,
  notFound,
  stubFetch,
} from '@/test-utils'
import { useToasts } from '@/ui'
import LibraryView from '@/views/LibraryView.vue'

vi.mock('@/api/upload', () => ({ uploadPage: vi.fn() }))
const upload = vi.mocked(uploadPage)

beforeEach(() => {
  upload.mockReset()
  // Busy pages are followed with timers; these tests don't wait for them.
  vi.useFakeTimers({ toFake: ['setTimeout'] })
})

afterEach(() => {
  vi.useRealTimers()
})

/** A tiny API: the journals on the shelf (cursors count from the start), and their pages. */
function serve(journals: Journal[], pages: Page[] = []) {
  const server = { journals: [...journals], deleted: [] as string[] }
  stubFetch((request) => {
    const url = new URL(request.url)
    const path = url.pathname.replace('/api/v1', '')
    const query = url.searchParams
    if (path === '/journals') {
      const from = Number(query.get('cursor') ?? 0)
      const to = from + Number(query.get('limit'))
      const items = server.journals.slice(from, to)
      return json({ items, nextCursor: to < server.journals.length ? String(to) : null })
    }
    const [, journalId] = path.match(/^\/journals\/([^/]+)$/) ?? []
    const journal = server.journals.find((j) => j.id === journalId)
    if (journal && request.method === 'DELETE') {
      server.deleted.push(journal.id)
      server.journals = server.journals.filter((j) => j !== journal)
      return new Response(null, { status: 204 })
    }
    if (journal) return json(journal)
    if (path === '/pages') {
      const status = query.get('status')
      const items = pages.filter(
        (page) => page.journalId === query.get('journalId') && (!status || page.status === status),
      )
      return json({ items, nextCursor: null })
    }
    return notFound()
  })
  return server
}

function open(path = '/') {
  return mountRoute(
    [
      { path: '/', name: 'library', component: LibraryView },
      { path: '/journals/:journalId', name: 'journal', component: LibraryView, props: true },
      { path: '/pages/:pageId', name: 'page', component: Elsewhere },
    ],
    path,
  )
}

function photo(name: string, type = 'image/jpeg') {
  return new File(['x'], name, { type })
}

async function pick(view: VueWrapper, ...files: File[]) {
  const input = view.get('input[type="file"]')
  Object.defineProperty(input.element, 'files', { value: files, configurable: true })
  await input.trigger('change')
  await flushPromises()
}

const lastToast = () => useToasts().items.value.at(-1)

describe('the library view', () => {
  it('opens the first journal on the shelf, shows its pages, and turns the shelf', async () => {
    const journals = [1, 2, 3, 4, 5].map((n) =>
      makeJournal({ name: `Journal ${n}`, pageCount: n === 1 ? 30 : 0 }),
    )
    const first = journals[0]!
    serve(
      journals,
      [1, 2].map((n) => makePage({ journalId: first.id, pageNumber: n })),
    )
    const { wrapper, router } = await open()

    expect(router.currentRoute.value.fullPath).toBe(`/journals/${first.id}`)
    expect(wrapper.text()).toContain('Journals 1–4')
    expect(wrapper.findAll('a[href^="/pages/"]')).toHaveLength(2)
    expect(wrapper.text()).toContain('Showing 2 of 30 pages')

    await wrapper.get('button[aria-label="More journals"]').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Journals 5–5')
    expect(wrapper.text()).toContain('Journal 5')
  })

  it('sends photos into the open journal, and says how each one is doing', async () => {
    const journal = makeJournal({ name: 'Green notebook' })
    serve([journal])
    const page = makePage({ journalId: journal.id, pageNumber: 49, status: 'uploaded' })
    upload.mockResolvedValue({ items: [{ filename: 'a.jpg', page, duplicate: false, job: null }] })
    const { wrapper } = await open(`/journals/${journal.id}`)

    await pick(wrapper, photo('IMG_1.jpg'), photo('notes.pdf', 'application/pdf'))

    expect(upload).toHaveBeenCalledOnce()
    expect(wrapper.text()).toContain('2 photos into Green notebook')
    expect(wrapper.text()).toContain('Not a photo')
    expect(wrapper.text()).toContain('Photos only: JPEG, PNG, HEIC or WebP')
    expect(wrapper.text()).toContain('Page 49 · waiting its turn')
    expect(button(wrapper, 'Hide each photo').attributes('aria-expanded')).toBe('true')
  })

  it('turns away files that aren’t photos', async () => {
    const journal = makeJournal()
    serve([journal])
    const { wrapper } = await open(`/journals/${journal.id}`)

    await pick(wrapper, photo('notes.pdf', 'application/pdf'))

    expect(upload).not.toHaveBeenCalled()
    expect(lastToast()).toMatchObject({
      tone: 'error',
      title: 'notes.pdf isn’t a photo',
      detail: 'Photos only: JPEG, PNG, HEIC or WebP, up to 25 MB each. PDF import is coming.',
    })
  })

  it('deletes the open journal after asking, then opens the first one left', async () => {
    const garden = makeJournal({ name: 'Green notebook', pageCount: 2 })
    const travel = makeJournal({ name: 'Travel journal' })
    const server = serve([garden, travel])
    const { wrapper, router } = await open(`/journals/${garden.id}`)

    await wrapper.get('button[aria-label="Delete journal"]').trigger('click')
    const dialog = wrapper.get('dialog[open]')
    expect(dialog.text()).toContain('Delete Green notebook?')
    expect(dialog.text()).toContain('Its 2 pages and all their text go with it.')
    const confirm = dialog.findAll('button').find((b) => b.text() === 'Delete journal')!
    await confirm.trigger('click')
    await flushPromises()

    expect(server.deleted).toEqual([garden.id])
    expect(router.currentRoute.value.fullPath).toBe(`/journals/${travel.id}`)
    expect(lastToast()?.title).toBe('Green notebook is gone')
  })

  it('shows only the pages that need a hand, and says when none do', async () => {
    const journal = makeJournal({ pageCount: 1 })
    serve([journal], [makePage({ journalId: journal.id })])
    const { wrapper } = await open(`/journals/${journal.id}`)

    await wrapper.get('select').setValue('failed')
    await flushPromises()
    expect(wrapper.text()).toContain('No pages need a hand right now.')

    await button(wrapper, 'Show all pages').trigger('click')
    await flushPromises()
    expect(wrapper.findAll('a[href^="/pages/"]')).toHaveLength(1)
  })

  it('goes back to the shelf when a journal is gone', async () => {
    serve([makeJournal()])
    const { router } = await open('/journals/jrn_01000000000000000000000000')

    expect(lastToast()?.title).toBe('That journal is gone')
    expect(router.currentRoute.value.name).toBe('library')
  })
})
