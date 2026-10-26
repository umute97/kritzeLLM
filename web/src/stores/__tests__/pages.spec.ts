import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { PAGE_BATCH, usePages } from '@/stores/pages'
import { calledUrl, json, makePage } from '@/test-utils'

beforeEach(() => {
  setActivePinia(createPinia())
})

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

describe('the page list', () => {
  it('loads a journal’s pages and shows more with the cursor', async () => {
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(json({ items: [makePage({ pageNumber: 1 })], nextCursor: 'jrn_1.1' }))
      .mockResolvedValueOnce(json({ items: [makePage({ pageNumber: 2 })], nextCursor: null }))
    vi.stubGlobal('fetch', fetch)
    const pages = usePages()

    await pages.load('jrn_1', 'ready')
    expect(calledUrl(fetch)).toBe(`/api/v1/pages?journalId=jrn_1&status=ready&limit=${PAGE_BATCH}`)
    await pages.more()
    expect(calledUrl(fetch, 1)).toContain('cursor=jrn_1.1')
    expect(pages.items.map((p) => p.pageNumber)).toEqual([1, 2])
    expect(pages.nextCursor).toBeNull()

    await pages.more()
    expect(fetch).toHaveBeenCalledTimes(2)
  })

  it('slots new pages in by number, and only where they belong', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        json({
          items: [makePage({ pageNumber: 1 }), makePage({ pageNumber: 3 })],
          nextCursor: null,
        }),
      ),
    )
    const pages = usePages()
    await pages.load('jrn_1')

    pages.put(makePage({ pageNumber: 2 }))
    pages.put(makePage({ pageNumber: 9, journalId: 'jrn_other' }))
    expect(pages.items.map((p) => p.pageNumber)).toEqual([1, 2, 3])
  })

  it('drops a page from a filtered list once it no longer fits', async () => {
    const failed = makePage({ pageNumber: 4, status: 'failed' })
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => json({ items: [failed], nextCursor: null })),
    )
    const pages = usePages()
    await pages.load('jrn_1', 'failed')

    pages.put({ ...failed, status: 'ready' })
    expect(pages.items).toEqual([])
    expect(pages.byId.get(failed.id)?.status).toBe('ready')
  })

  it('follows a busy page until it’s ready', async () => {
    vi.useFakeTimers()
    const page = makePage({ status: 'transcribing' })
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(json({ ...page, status: 'indexing' }))
      .mockResolvedValueOnce(json({ ...page, status: 'ready' }))
    vi.stubGlobal('fetch', fetch)
    const pages = usePages()

    pages.put(page)
    await vi.advanceTimersByTimeAsync(2000)
    expect(pages.byId.get(page.id)?.status).toBe('indexing')
    await vi.advanceTimersByTimeAsync(2000)
    expect(pages.byId.get(page.id)?.status).toBe('ready')
    await vi.advanceTimersByTimeAsync(10_000)
    expect(fetch).toHaveBeenCalledTimes(2)
  })

  it('forgets a page that was deleted elsewhere', async () => {
    vi.useFakeTimers()
    const page = makePage({ status: 'uploaded' })
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => json({ title: 'Not found', status: 404 }, 404)),
    )
    const pages = usePages()
    pages.put(page)
    await vi.advanceTimersByTimeAsync(2000)
    expect(pages.byId.has(page.id)).toBe(false)
  })

  it('forgets a deleted journal’s pages and stops following them', async () => {
    vi.useFakeTimers()
    const fetch = vi.fn()
    vi.stubGlobal('fetch', fetch)
    const pages = usePages()
    const gone = makePage({ journalId: 'jrn_1', status: 'uploaded' })
    const kept = makePage({ journalId: 'jrn_2' })
    pages.put(gone)
    pages.put(kept)

    pages.forgetJournal('jrn_1')
    expect([...pages.byId.keys()]).toEqual([kept.id])
    await vi.advanceTimersByTimeAsync(2000)
    expect(fetch).not.toHaveBeenCalled()
  })
})
