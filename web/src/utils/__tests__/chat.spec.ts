import { describe, expect, it } from 'vitest'

import { chips, paragraphs, tally } from '@/utils/chat'

describe('paragraphs', () => {
  it('splits an answer into paragraphs of text and runs of citations', () => {
    expect(
      paragraphs('You planted them by the fence [3][5], in March [1, 2].\n\nThey bloomed.'),
    ).toEqual([
      [
        { text: 'You planted them by the fence ' },
        { refs: [3, 5] },
        { text: ', in March ' },
        { refs: [1, 2] },
        { text: '.' },
      ],
      [{ text: 'They bloomed.' }],
    ])
  })

  it('keeps single line breaks and leaves other brackets alone', () => {
    expect(paragraphs('Dear diary,\nrain [?] again [a1].\n\n\n')).toEqual([
      [{ text: 'Dear diary,\nrain [?] again [a1].' }],
    ])
  })
})

describe('chips', () => {
  const source = (ref: number, pageId: string) => ({ ref, pageId })
  const sources = new Map([
    [1, source(1, 'pg_12')],
    [2, source(2, 'pg_14')],
    [3, source(3, 'pg_12')],
  ])

  it('gives each cited page one chip, in order, standing for all its citations', () => {
    expect(chips([3, 2, 1, 9], sources)).toEqual([
      { source: source(3, 'pg_12'), refs: [3, 1] },
      { source: source(2, 'pg_14'), refs: [2] },
    ])
  })
})

describe('tally', () => {
  it('counts searches, pages read and browsing', () => {
    const names = ['search_journal', 'find_exact', 'read_page', 'read_block', 'list_pages', 'oops']
    expect(tally(names.map((name) => ({ name })))).toEqual({ searches: 2, reads: 2, browses: 1 })
  })
})
