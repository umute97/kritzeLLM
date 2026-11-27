import { ref } from 'vue'

const KEY = 'kritzellm.recentSearches'
const KEEP = 5

// Private windows and blocked site data can throw on any access; then nothing is remembered.
function read(): string[] {
  try {
    const saved: unknown = JSON.parse(globalThis.localStorage.getItem(KEY) ?? '[]')
    return Array.isArray(saved)
      ? saved.filter((item): item is string => typeof item === 'string').slice(0, KEEP)
      : []
  } catch {
    return []
  }
}

/** The last few searches on this device, newest first. */
export function useRecentSearches() {
  const items = ref(read())

  function add(query: string) {
    const lower = query.toLowerCase()
    items.value = [query, ...items.value.filter((item) => item.toLowerCase() !== lower)].slice(
      0,
      KEEP,
    )
    try {
      globalThis.localStorage.setItem(KEY, JSON.stringify(items.value))
    } catch {
      // Still listed for this visit.
    }
  }

  return { items, add }
}
