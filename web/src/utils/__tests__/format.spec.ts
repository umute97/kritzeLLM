import { describe, expect, it } from 'vitest'

import { coverColor } from '@/utils/covers'
import { fileSize, formatDay, formatEntryDates, plural } from '@/utils/format'

const now = new Date('2026-10-24T12:00:00')

describe('format', () => {
  it('writes days short, with the year only when it isn’t this one', () => {
    expect(formatDay('2026-03-03', now)).toBe('Mar 3')
    expect(formatDay('2024-03-03', now)).toBe('Mar 3, 2024')
  })

  it('sums up entry dates', () => {
    expect(formatEntryDates([], now)).toBeUndefined()
    expect(formatEntryDates(['2026-03-03'], now)).toBe('Mar 3')
    expect(formatEntryDates(['2026-03-05', '2026-03-03', '2026-03-04'], now)).toBe('Mar 3 – Mar 5')
  })

  it('counts and sizes things', () => {
    expect(plural(1, 'page')).toBe('1 page')
    expect(plural(48, 'page')).toBe('48 pages')
    expect(fileSize(3_250_586)).toBe('3.1 MB')
    expect(fileSize(25 * 1024 * 1024)).toBe('25 MB')
    expect(fileSize(200)).toBe('1 KB')
  })

  it('gives a journal the same cover every time', () => {
    expect(coverColor('jrn_abc')).toBe(coverColor('jrn_abc'))
    expect(['herb', 'clay', 'orchid', 'lemon']).toContain(coverColor('jrn_xyz'))
  })
})
