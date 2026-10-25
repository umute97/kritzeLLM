const thisYear = new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric' })
const otherYear = new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric', year: 'numeric' })

/** "Mar 3", or "Mar 3, 2024" when it's not this year. Takes a `YYYY-MM-DD` day. */
export function formatDay(day: string, now = new Date()): string {
  const date = new Date(`${day}T00:00:00`)
  return (date.getFullYear() === now.getFullYear() ? thisYear : otherYear).format(date)
}

/** A page's entry dates in a few words: one day, or the first and last. */
export function formatEntryDates(days: string[], now = new Date()): string | undefined {
  if (days.length === 0) return undefined
  const sorted = [...days].sort()
  const first = formatDay(sorted[0]!, now)
  return sorted.length === 1 ? first : `${first} – ${formatDay(sorted.at(-1)!, now)}`
}

export function plural(count: number, one: string, many = `${one}s`): string {
  return `${count} ${count === 1 ? one : many}`
}

export function fileSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1).replace(/\.0$/, '')} MB`
}
