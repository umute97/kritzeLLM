import type { CoverColor } from '@/ui'

const colors: CoverColor[] = ['herb', 'clay', 'orchid', 'lemon']

/** A journal keeps the same cover colour wherever it shows up. */
export function coverColor(id: string): CoverColor {
  let hash = 0
  for (const char of id) hash = (hash * 31 + char.charCodeAt(0)) >>> 0
  return colors[hash % colors.length]!
}
