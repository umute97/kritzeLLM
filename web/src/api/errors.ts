import type { Problem } from './types'

/** A failed API call, carrying the server's problem+json (or one made up for network trouble). */
export class ApiError extends Error {
  readonly problem: Problem

  constructor(problem: Problem, options?: ErrorOptions) {
    super(problem.detail ?? problem.title, options)
    this.name = 'ApiError'
    this.problem = problem
  }

  get status(): number {
    return this.problem.status
  }

  /** The request never got an answer: the API is down or the network is gone. */
  get offline(): boolean {
    return this.problem.status === 0
  }
}

export const offlineProblem: Problem = {
  type: 'about:blank',
  title: 'Can’t reach kritzeLLM',
  status: 0,
  detail: 'The API didn’t answer. Is the stack running?',
}

function isProblem(value: unknown): value is Problem {
  return typeof value === 'object' && value !== null && 'title' in value && 'status' in value
}

/** The body of a failed response as a Problem, with a fallback for non-problem bodies. */
export function toProblem(body: unknown, response: Response): Problem {
  if (isProblem(body)) return body
  return {
    type: 'about:blank',
    title: response.statusText || 'Something went wrong',
    status: response.status,
    detail: null,
  }
}
