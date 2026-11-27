import type { Block, SearchHit } from '@/api/types'
import type { Mark, Quote } from '@/ui'

const LETTER = String.raw`[\p{L}\p{N}]`
const GAP = String.raw`[^\p{L}\p{N}]+`
const WORDS = /[\p{L}\p{N}]+/gu
// Web search syntax, as `websearch_to_tsquery` reads it: "a phrase", a word, or -left-out.
const PARTS = /(-?)"([^"]*)"?|(\S+)/g

/** A phrase of whole words, with anything that isn't a letter between them, as Postgres reads it. */
function phrase(text: string): string | undefined {
  const words = text.match(WORDS)
  if (!words) return undefined
  return `(?<!${LETTER})${words.join(GAP)}(?!${LETTER})`
}

/**
 * What to mark in the hits of a search, ignoring case: the query's words and quoted phrases as
 * whole words (minus `or` and left-out `-words`).
 */
export function matcher(query: string): RegExp | undefined {
  const phrases: string[] = []
  for (const [, left, quoted, bare] of query.matchAll(PARTS)) {
    if (left || bare?.startsWith('-') || bare?.toLowerCase() === 'or') continue
    const pattern = phrase(quoted ?? bare ?? '')
    if (pattern) phrases.push(pattern)
  }
  if (phrases.length === 0) return undefined
  // Longest first, so a phrase wins over a word inside it.
  phrases.sort((a, b) => b.length - a.length)
  return new RegExp(phrases.join('|'), 'giu')
}

export function findMarks(text: string, pattern: RegExp | undefined): Mark[] {
  if (!pattern) return []
  return [...text.matchAll(pattern)]
    .filter((match) => match[0].length > 0)
    .map((match) => [match.index, match.index + match[0].length])
}

const LONGEST = 240
const LEAD = 60

/** A long text cut to a window around its first mark, with `…` where it was cut. */
export function excerpt(text: string, marks: Mark[]): { text: string; marks: Mark[] } {
  if (text.length <= LONGEST) return { text, marks }
  const [first, firstEnd] = marks[0] ?? [0, 0]
  let start = Math.max(0, Math.min(first - LEAD, text.length - LONGEST))
  if (start > 0) {
    const space = text.slice(start, first).search(/\s/)
    if (space !== -1) start += space + 1
  }
  let end = Math.min(text.length, start + LONGEST)
  if (end < text.length) {
    const space = text.slice(firstEnd, end).search(/\s\S*$/)
    if (space !== -1) end = firstEnd + space
  }
  const before = start > 0 ? '…' : ''
  const shift = before.length - start
  return {
    text: `${before}${text.slice(start, end)}${end < text.length ? '…' : ''}`,
    marks: marks
      .filter(([from, to]) => from >= start && to <= end)
      .map(([from, to]) => [from + shift, to + shift]),
  }
}

const QUOTES = 3

/**
 * The few blocks of a hit worth quoting: those with a match, else the first, each cut around its
 * first match. `more` counts the matched blocks left out.
 */
export function pickQuotes(
  blocks: Block[],
  pattern: RegExp | undefined,
): { quotes: Quote[]; more: number } {
  const all = blocks.map((block) => ({ block, marks: findMarks(block.text, pattern) }))
  const matching = all.filter(({ marks }) => marks.length > 0)
  const picked = matching.length ? matching.slice(0, QUOTES) : all.slice(0, 1)
  return {
    quotes: picked.map(({ block, marks }) => ({ kind: block.kind, ...excerpt(block.text, marks) })),
    more: blocks.length - picked.length,
  }
}

/** Hits by their page's first entry date, newest first; undated pages keep their order at the end. */
export function newestFirst(hits: SearchHit[]): SearchHit[] {
  const day = (hit: SearchHit) => [...hit.page.entryDates].sort()[0] ?? ''
  return [...hits].sort((a, b) => day(b).localeCompare(day(a)))
}
