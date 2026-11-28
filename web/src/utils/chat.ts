// An answer's text cites blocks as `[3]` (or `[2, 5]`); the server keeps only the ones it read.
// Citations side by side, like `[3][5]`, are read as one run.
const CITATIONS = /\[\d+(?:\s*,\s*\d+)*\](?:\s*\[\d+(?:\s*,\s*\d+)*\])*/g

export type Piece = { text: string } | { refs: number[] }

/** An answer as paragraphs, each its text and runs of citations in order. */
export function paragraphs(content: string): Piece[][] {
  return content
    .split(/\n\s*\n/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean)
    .map((paragraph) => {
      const pieces: Piece[] = []
      let at = 0
      for (const match of paragraph.matchAll(CITATIONS)) {
        if (match.index > at) pieces.push({ text: paragraph.slice(at, match.index) })
        pieces.push({ refs: match[0].match(/\d+/g)!.map(Number) })
        at = match.index + match[0].length
      }
      if (at < paragraph.length) pieces.push({ text: paragraph.slice(at) })
      return pieces
    })
}

/** A run of citations as chips: one per page, in order, each with the citations it stands for. */
export function chips<S extends { ref: number; pageId: string }>(
  refs: number[],
  sources: Map<number, S>,
): { source: S; refs: number[] }[] {
  const byPage = new Map<string, { source: S; refs: number[] }>()
  for (const ref of refs) {
    const source = sources.get(ref)
    if (!source) continue
    const chip = byPage.get(source.pageId)
    if (chip) chip.refs.push(ref)
    else byPage.set(source.pageId, { source, refs: [ref] })
  }
  return [...byPage.values()]
}

/**
 * One thing the helper did to answer: a tool call, and how many pages it found once done. A saved
 * answer's tool calls are steps already; only streamed ones carry the `id` their result matches.
 */
export interface Step {
  id?: string
  name: string
  args: Record<string, unknown>
  pages?: number
}

export type StepKind = 'search' | 'exact' | 'list' | 'page' | 'block' | 'other'

const KINDS: Record<string, StepKind> = {
  search_journal: 'search',
  find_exact: 'exact',
  list_pages: 'list',
  read_page: 'page',
  read_block: 'block',
}

export function stepKind(name: string): StepKind {
  return KINDS[name] ?? 'other'
}

/** What a search step looked for. */
export function lookedFor(step: Step): string {
  return String(step.args.query ?? step.args.text ?? '')
}

/** What an answer took, for "searched twice, read 4 pages". */
export function tally(steps: Pick<Step, 'name'>[]): {
  searches: number
  reads: number
  browses: number
} {
  const count = (...kinds: StepKind[]) =>
    steps.filter((step) => kinds.includes(stepKind(step.name))).length
  return {
    searches: count('search', 'exact'),
    reads: count('page', 'block'),
    browses: count('list'),
  }
}
