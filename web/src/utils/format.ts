import { currentLocale, type Locale } from '@/i18n'

const days = new Map<string, Intl.DateTimeFormat>()

function dayFormat(locale: Locale, withYear: boolean): Intl.DateTimeFormat {
  const key = `${locale}:${withYear}`
  let format = days.get(key)
  if (!format) {
    format = new Intl.DateTimeFormat(locale, {
      month: 'short',
      day: 'numeric',
      year: withYear ? 'numeric' : undefined,
    })
    days.set(key, format)
  }
  return format
}

/** "Mar 3", or "Mar 3, 2024" when it's not this year. Takes a `YYYY-MM-DD` day. */
export function formatDay(day: string, now = new Date()): string {
  const date = new Date(`${day}T00:00:00`)
  return dayFormat(currentLocale(), date.getFullYear() !== now.getFullYear()).format(date)
}

/** A page's entry dates in a few words: one day, or the first and last. */
export function formatEntryDates(days: string[], now = new Date()): string | undefined {
  if (days.length === 0) return undefined
  const sorted = [...days].sort()
  const first = formatDay(sorted[0]!, now)
  return sorted.length === 1 ? first : `${first} – ${formatDay(sorted.at(-1)!, now)}`
}

export function fileSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`
  const megabytes = new Intl.NumberFormat(currentLocale(), { maximumFractionDigits: 1 })
  return `${megabytes.format(bytes / (1024 * 1024))} MB`
}
