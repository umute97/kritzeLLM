import { afterEach, describe, expect, it } from 'vitest'

import { coverColor } from '@/utils/covers'
import { setLocale } from '@/i18n'
import { fileSize, formatDay, formatEntryDates, formatRecent } from '@/utils/format'

const now = new Date('2026-10-24T12:00:00')

afterEach(() => setLocale('en'))

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

  it('writes days the German way in German', () => {
    setLocale('de')
    expect(formatDay('2026-03-03', now)).toBe('3. März')
    expect(formatDay('2024-03-03', now)).toBe('3. März 2024')
  })

  it('says when something happened lately the way people do', () => {
    // `now` is Saturday, October 24th.
    expect(formatRecent('2026-10-24T08:00:00', now)).toBe('today')
    expect(formatRecent('2026-10-23T23:30:00', now)).toBe('yesterday')
    expect(formatRecent('2026-10-20T10:00:00', now)).toBe('Tuesday')
    expect(formatRecent('2026-10-17T10:00:00', now)).toBe('Oct 17')
    expect(formatRecent('2025-12-24T10:00:00', now)).toBe('Dec 24, 2025')
    setLocale('de')
    expect(formatRecent('2026-10-23T23:30:00', now)).toBe('gestern')
    expect(formatRecent('2026-10-20T10:00:00', now)).toBe('Dienstag')
  })

  it('sizes files', () => {
    expect(fileSize(3_250_586)).toBe('3.1 MB')
    expect(fileSize(25 * 1024 * 1024)).toBe('25 MB')
    expect(fileSize(200)).toBe('1 KB')
    expect(fileSize(0)).toBe('0 KB')
    setLocale('de')
    expect(fileSize(3_250_586)).toBe('3,1 MB')
  })

  it('gives a journal the same cover every time', () => {
    expect(coverColor('jrn_abc')).toBe(coverColor('jrn_abc'))
    expect(['herb', 'clay', 'orchid', 'lemon']).toContain(coverColor('jrn_xyz'))
  })
})
