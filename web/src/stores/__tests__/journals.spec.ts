import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useJournals } from '@/stores/journals'
import { calledUrl, json, makeJournal } from '@/test-utils'

beforeEach(() => {
  setActivePinia(createPinia())
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('the shelf', () => {
  it('pages with the cursor and only knows whether there are more', async () => {
    const first = [1, 2, 3, 4].map((n) => makeJournal({ name: `Journal ${n}` }))
    const second = [makeJournal({ name: 'Journal 5' })]
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(json({ items: first, nextCursor: first[3]!.id }))
      .mockResolvedValueOnce(json({ items: second, nextCursor: null }))
    vi.stubGlobal('fetch', fetch)
    const journals = useJournals()

    await journals.show(0)
    expect(journals.range).toBe('Journals 1–4')
    expect(journals.canBack).toBe(false)
    expect(journals.canNext).toBe(true)
    expect(calledUrl(fetch)).toBe('/api/v1/journals?limit=4')

    await journals.next()
    expect(calledUrl(fetch, 1)).toBe(`/api/v1/journals?limit=4&cursor=${first[3]!.id}`)
    expect(journals.shelf.map((j) => j.name)).toEqual(['Journal 5'])
    expect(journals.range).toBe('Journals 5–5')
    expect(journals.canNext).toBe(false)

    await journals.back()
    expect(fetch).toHaveBeenCalledTimes(2)
    expect(journals.shelf).toHaveLength(4)
  })

  it('knows when the shelf is empty', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => json({ items: [], nextCursor: null })),
    )
    const journals = useJournals()
    expect(journals.empty).toBe(false)
    await journals.show(0)
    expect(journals.empty).toBe(true)
  })

  it('looks a journal up once and keeps it', async () => {
    const journal = makeJournal()
    const fetch = vi.fn(async () => json(journal))
    vi.stubGlobal('fetch', fetch)
    const journals = useJournals()
    expect(await journals.get(journal.id)).toEqual(journal)
    expect(await journals.get(journal.id)).toEqual(journal)
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('shows a refreshed page count on the shelf', async () => {
    const journal = makeJournal({ pageCount: 0 })
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce(json({ items: [journal], nextCursor: null }))
        .mockResolvedValueOnce(json({ ...journal, pageCount: 2 })),
    )
    const journals = useJournals()
    await journals.show(0)
    await journals.refresh(journal.id)
    expect(journals.shelf[0]?.pageCount).toBe(2)
  })
})
