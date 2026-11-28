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

function localDay(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

/** When something last happened: "today", "yesterday", a weekday within the week, else a day. */
export function formatRecent(timestamp: string, now = new Date()): string {
  const date = new Date(timestamp)
  const midnight = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime()
  const daysAgo = Math.round((midnight(now) - midnight(date)) / 86_400_000)
  const locale = currentLocale()
  if (daysAgo >= 0 && daysAgo <= 1) {
    return new Intl.RelativeTimeFormat(locale, { numeric: 'auto' }).format(-daysAgo, 'day')
  }
  if (daysAgo > 1 && daysAgo < 7) {
    return new Intl.DateTimeFormat(locale, { weekday: 'long' }).format(date)
  }
  return formatDay(localDay(date), now)
}

/** "3.1 MB", or "1 KB" for anything at all under a kilobyte. */
export function fileSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${bytes && Math.max(1, Math.round(bytes / 1024))} KB`
  const megabytes = new Intl.NumberFormat(currentLocale(), { maximumFractionDigits: 1 })
  return `${megabytes.format(bytes / (1024 * 1024))} MB`
}
