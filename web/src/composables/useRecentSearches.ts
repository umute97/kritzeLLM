import { ref } from 'vue'

import { readStored, writeStored } from '@/utils/storage'

const KEY = 'kritzellm.recentSearches'
const KEEP = 5

function read(): string[] {
  try {
    const saved: unknown = JSON.parse(readStored(KEY) ?? '[]')
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
    writeStored(KEY, JSON.stringify(items.value))
  }

  return { items, add }
}
