import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '@/api/errors'
import type { UploadResult } from '@/api/types'
import { uploadPage } from '@/api/upload'
import { usePages } from '@/stores/pages'
import { MAX_BYTES, rejectReason, useUploads } from '@/stores/uploads'
import { json, makeJournal, makePage } from '@/test-utils'
import { useToasts } from '@/ui'

vi.mock('@/api/upload', () => ({ uploadPage: vi.fn() }))
const upload = vi.mocked(uploadPage)

function photo(name = 'IMG_2041.jpg', size = 1000, type = 'image/jpeg') {
  const file = new File(['x'], name, { type })
  Object.defineProperty(file, 'size', { value: size })
  return file
}

function result(overrides: Partial<UploadResult['items'][number]> = {}): UploadResult {
  return { items: [{ filename: 'x', page: makePage(), duplicate: false, job: null, ...overrides }] }
}

beforeEach(() => {
  setActivePinia(createPinia())
  upload.mockReset()
  // Refreshing the journal's page count afterwards.
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => json(makeJournal({ id: 'jrn_1' }))),
  )
})

afterEach(() => {
  useToasts().clear()
  vi.unstubAllGlobals()
})

describe('rejectReason', () => {
  it('takes photos the API takes, HEIC without a type included', () => {
    expect(rejectReason(photo())).toBeNull()
    expect(rejectReason(photo('IMG_1.HEIC', 1000, ''))).toBeNull()
    expect(rejectReason(photo('notes.pdf', 1000, 'application/pdf'))?.label).toBe('Not a photo')
    expect(rejectReason(photo('big.png', MAX_BYTES + 1, 'image/png'))?.label).toBe('Too big')
  })
})

describe('useUploads', () => {
  it('says why when nothing can go up', () => {
    const uploads = useUploads()
    expect(uploads.add('jrn_1', [photo('notes.pdf', 10, 'application/pdf')])).toBe(
      'notes.pdf isn’t a photo',
    )
    expect(uploads.rows).toEqual([])
    expect(upload).not.toHaveBeenCalled()
  })

  it('sends good photos one by one and lists the rest as failed', async () => {
    const page = makePage({ pageNumber: 49, status: 'uploaded' })
    let finish!: (value: UploadResult) => void
    upload.mockImplementation((_journal, _file, onProgress) => {
      onProgress(500, 1000)
      return new Promise((resolve) => (finish = resolve))
    })
    const uploads = useUploads()

    expect(uploads.add('jrn_1', [photo(), photo('notes.pdf', 10, 'application/pdf')])).toBeNull()
    expect(uploads.rows.map((r) => r.status)).toEqual(['sending', 'failed'])
    expect(uploads.rows[0]!.progress).toBe(50)
    expect(uploads.rows[1]!.statusLabel).toBe('Not a photo')

    finish(result({ page }))
    await vi.waitFor(() => expect(uploads.rows[0]!.status).toBe('queued'))
    expect(uploads.rows[0]!.note).toBe('Page 49 · waiting its turn')

    usePages().put({ ...page, status: 'ready' })
    expect(uploads.rows[0]!.status).toBe('ready')
    expect(uploads.active).toBe(false)
    expect(useToasts().items.value[0]?.title).toBe('Pages tucked in')
  })

  it('marks duplicates as already here', async () => {
    upload.mockResolvedValue(result({ page: makePage({ pageNumber: 12 }), duplicate: true }))
    const uploads = useUploads()
    uploads.add('jrn_1', [photo()])
    await vi.waitFor(() => expect(uploads.rows[0]!.status).toBe('duplicate'))
    expect(uploads.rows[0]!.note).toBe('Same photo as page 12')
    expect(useToasts().items.value).toEqual([])
  })

  it('shows the server’s reason and stops the queue when the API is gone', async () => {
    upload
      .mockRejectedValueOnce(
        new ApiError({
          type: 'about:blank',
          title: 'Content Too Large',
          status: 413,
          detail: 'Over 25 MB.',
        }),
      )
      .mockRejectedValueOnce(new ApiError({ type: 'about:blank', title: 'Offline', status: 0 }))
    const uploads = useUploads()
    uploads.add('jrn_1', [photo('a.jpg'), photo('b.jpg'), photo('c.jpg')])

    await vi.waitFor(() => expect(uploads.rows.every((r) => r.status === 'failed')).toBe(true))
    expect(uploads.rows[0]).toMatchObject({ statusLabel: 'Too big', note: 'Over 25 MB.' })
    expect(uploads.rows[2]!.note).toBe('Didn’t go up, try again')
    expect(upload).toHaveBeenCalledTimes(2)
  })
})
