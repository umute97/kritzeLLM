import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '@/api/errors'
import type { UploadResult } from '@/api/types'
import { uploadPage } from '@/api/upload'
import { usePages } from '@/stores/pages'
import { rejectReason, useUploads } from '@/stores/uploads'
import { json, makeJournal, makePage, problem } from '@/test-utils'
import { useToasts } from '@/ui'
import { MAX_BYTES } from '@/utils/photos'

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
  upload.mockReset()
  // Refreshing the journal's page count afterwards.
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => json(makeJournal({ id: 'jrn_1' }))),
  )
})

describe('rejectReason', () => {
  it('takes photos the API takes, HEIC without a type included', () => {
    expect(rejectReason(photo())).toBeNull()
    expect(rejectReason(photo('IMG_1.HEIC', 1000, ''))).toBeNull()
    expect(rejectReason(photo('notes.pdf', 1000, 'application/pdf'))).toBe('type')
    expect(rejectReason(photo('big.png', MAX_BYTES + 1, 'image/png'))).toBe('size')
  })
})

describe('useUploads', () => {
  it('says why when nothing can go up', () => {
    const uploads = useUploads()
    const pdf = photo('notes.pdf', 10, 'application/pdf')
    expect(uploads.add('jrn_1', [pdf])).toEqual({ file: pdf, reason: 'type' })
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
    expect(uploads.rows[0]).toMatchObject({ sent: 500, total: 1000 })
    expect(uploads.rows[1]).toMatchObject({ reason: 'type', total: 10 })

    finish(result({ page }))
    await vi.waitFor(() => expect(uploads.rows[0]!.status).toBe('queued'))
    expect(uploads.rows[0]!.pageNumber).toBe(49)

    usePages().put({ ...page, status: 'ready' })
    expect(uploads.rows[0]!.status).toBe('ready')
    expect(uploads.batch('jrn_1').active).toBe(false)
    expect(useToasts().items.value[0]?.title).toBe('Pages tucked in')
  })

  it('marks duplicates as already here', async () => {
    upload.mockResolvedValue(result({ page: makePage({ pageNumber: 12 }), duplicate: true }))
    const uploads = useUploads()
    uploads.add('jrn_1', [photo()])
    await vi.waitFor(() => expect(uploads.rows[0]!.status).toBe('duplicate'))
    expect(uploads.rows[0]!.pageNumber).toBe(12)
    expect(useToasts().items.value).toEqual([])
  })

  it('shows the server’s reason and stops the queue when the API is gone', async () => {
    const tooLarge = problem(413, 'Content Too Large', 'Over 25 MB.')
    upload
      .mockRejectedValueOnce(new ApiError(tooLarge))
      .mockRejectedValueOnce(new ApiError(problem(0, 'Offline')))
    const uploads = useUploads()
    uploads.add('jrn_1', [photo('a.jpg'), photo('b.jpg'), photo('c.jpg')])

    await vi.waitFor(() => expect(uploads.rows.every((r) => r.status === 'failed')).toBe(true))
    expect(uploads.rows[0]!.problem).toEqual(tooLarge)
    expect(uploads.rows[2]!.reason).toBe('stopped')
    expect(upload).toHaveBeenCalledTimes(2)
  })

  it('marks a row deleted once its page is, so the list can be cleared', async () => {
    const page = makePage({ status: 'uploaded' })
    upload.mockResolvedValue(result({ page }))
    const uploads = useUploads()
    uploads.add('jrn_1', [photo()])
    await vi.waitFor(() => expect(uploads.rows[0]!.status).toBe('queued'))
    expect(uploads.batch('jrn_1').active).toBe(true)

    usePages().forget(page.id)
    expect(uploads.rows[0]!.status).toBe('deleted')
    expect(uploads.batch('jrn_1').counts.deleted).toBe(1)
    expect(uploads.batch('jrn_1').active).toBe(false)
    uploads.clear('jrn_1')
    expect(uploads.rows).toEqual([])
  })

  it('keeps each journal’s rows to itself', async () => {
    upload.mockImplementation(async (journalId) =>
      result({
        page: makePage({ journalId, status: journalId === 'jrn_1' ? 'ready' : 'uploaded' }),
      }),
    )
    const uploads = useUploads()
    uploads.add('jrn_1', [photo('a.jpg')])
    uploads.add('jrn_2', [photo('b.jpg')])
    await vi.waitFor(() => expect(upload).toHaveBeenCalledTimes(2))
    await vi.waitFor(() => expect(uploads.batch('jrn_2').rows[0]?.status).toBe('queued'))

    expect(uploads.batch('jrn_1').rows.map((r) => r.fileName)).toEqual(['a.jpg'])
    expect(uploads.batch('jrn_1').active).toBe(false)
    expect(uploads.batch('jrn_2').active).toBe(true)
    // A busy journal doesn't stop another one's list from clearing.
    uploads.clear('jrn_1')
    uploads.clear('jrn_2')
    expect(uploads.rows.map((r) => r.fileName)).toEqual(['b.jpg'])
  })

  it('forgets a deleted journal’s rows and photos still waiting to go up', async () => {
    let finish!: (value: UploadResult) => void
    upload.mockImplementation(() => new Promise((resolve) => (finish = resolve)))
    const uploads = useUploads()
    uploads.add('jrn_1', [photo('a.jpg')])
    uploads.add('jrn_2', [photo('b.jpg'), photo('c.jpg')])

    uploads.forget('jrn_2')
    expect(uploads.rows.map((r) => r.fileName)).toEqual(['a.jpg'])
    finish(result())
    await vi.waitFor(() => expect(uploads.rows[0]!.status).toBe('ready'))
    expect(upload).toHaveBeenCalledTimes(1)
  })
})
