import { describe, expect, it } from 'vitest'

import type { SearchHit } from '@/api/types'
import { makeBlock, makePage } from '@/test-utils'
import type { Mark } from '@/ui'
import { excerpt, findMarks, matcher, newestFirst, pickQuotes } from '@/utils/search'

function marked(text: string, query: string) {
  return findMarks(text, matcher(query)).map(([start, end]) => text.slice(start, end))
}

describe('matcher', () => {
  it('marks the query’s words as whole words, ignoring case', () => {
    expect(marked('Sweet peas by the fence, peasant SWEETS. Sweet!', 'sweet PEAS')).toEqual([
      'Sweet',
      'peas',
      'Sweet',
    ])
    expect(marked('Über die Brücke ging Öma', 'über öma')).toEqual(['Über', 'Öma'])
  })

  it('keeps quoted phrases together and skips "or" and left-out words', () => {
    const text = 'sweet peas, then peas and sweet basil or mint'
    expect(marked(text, '"sweet peas" or basil -mint')).toEqual(['sweet peas', 'basil'])
    expect(marked(text, '-"sweet peas" basil')).toEqual(['basil'])
  })

  it('reads a phrase across punctuation and line breaks, like Postgres', () => {
    expect(marked('grandma’s cake and grandma\ns cake', 'grandma’s')).toEqual([
      'grandma’s',
      'grandma\ns',
    ])
  })

  it('marks nothing when the query has no words', () => {
    expect(matcher('?!')).toBeUndefined()
    expect(findMarks('anything', undefined)).toEqual([])
  })
})

describe('excerpt', () => {
  const long = `${'Morgens Regen. '.repeat(20)}Dann endlich die Wicken gepflanzt. ${'Abends Tee. '.repeat(20)}`

  it('leaves short text alone', () => {
    const marks: Mark[] = [[0, 5]]
    expect(excerpt('Short and sweet', marks)).toEqual({ text: 'Short and sweet', marks })
  })

  it('cuts long text around its first mark, at word breaks, and moves the marks along', () => {
    const at = long.indexOf('Wicken')
    const { text, marks } = excerpt(long, [[at, at + 6]])

    expect(text.length).toBeLessThanOrEqual(242)
    expect(text.startsWith('…') && text.endsWith('…')).toBe(true)
    const kept = text.slice(1, -1)
    const from = long.indexOf(kept)
    expect(from).toBeGreaterThan(0)
    expect(long[from - 1]).toMatch(/\s/)
    expect(long[from + kept.length]).toMatch(/\s/)
    expect(marks).toHaveLength(1)
    expect(text.slice(...marks[0]!)).toBe('Wicken')
  })

  it('starts at the beginning when nothing is marked', () => {
    const { text, marks } = excerpt(long, [])
    expect(text.startsWith('Morgens Regen.')).toBe(true)
    expect(text.endsWith('…')).toBe(true)
    expect(marks).toEqual([])
  })
})

describe('pickQuotes', () => {
  const blocks = ['Dear diary', 'Tea in the rain', 'More rain', 'Rain again', 'and rain'].map(
    (text, seq) => makeBlock({ seq, text }),
  )

  it('quotes up to three matching blocks, in reading order, and counts the rest', () => {
    const { quotes, more } = pickQuotes(blocks, matcher('rain'))

    expect(quotes.map((quote) => quote.text)).toEqual([
      'Tea in the rain',
      'More rain',
      'Rain again',
    ])
    expect(quotes[0]!.marks).toEqual([[11, 15]])
    expect(more).toBe(2)
  })

  it('quotes the first block when none has the words, e.g. a match by meaning', () => {
    const { quotes, more } = pickQuotes(blocks, matcher('cosy evening'))

    expect(quotes.map((quote) => [quote.text, quote.marks])).toEqual([['Dear diary', []]])
    expect(more).toBe(4)
  })
})

describe('newestFirst', () => {
  function hit(entryDates: string[]): SearchHit {
    return {
      page: makePage({ entryDates }),
      blocks: [],
      score: 0,
      vectorRank: null,
      keywordRank: null,
    }
  }

  it('orders hits by their first entry date, newest first, with undated ones last as they were', () => {
    const undated = hit([])
    const march = hit(['2026-03-28', '2026-03-03'])
    const later = hit([])
    const june = hit(['2025-06-02'])
    const april = hit(['2026-04-01'])

    expect(newestFirst([undated, march, later, june, april])).toEqual([
      april,
      march,
      june,
      undated,
      later,
    ])
  })
})
