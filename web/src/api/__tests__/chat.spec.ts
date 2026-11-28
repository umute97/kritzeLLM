import { describe, expect, it, vi } from 'vitest'

import { BrokenStreamError, streamAnswer } from '@/api/chat'
import { configureApi } from '@/api/client'
import { ApiError } from '@/api/errors'
import type { ChatStreamEvent } from '@/api/types'
import { eventStream, json, makeMessage, makeSource, problem } from '@/test-utils'

/** Answers with `stream`, which fails the way a browser's does when the request is called off. */
function serve(stream: ReturnType<typeof eventStream>) {
  const fetch = vi.fn<(request: Request) => Promise<Response>>(async (request) => {
    request.signal.addEventListener('abort', () =>
      stream.fail(new DOMException('The operation was aborted.', 'AbortError')),
    )
    return stream.response()
  })
  vi.stubGlobal('fetch', fetch)
  return fetch
}

function ask(signal?: AbortSignal) {
  const events: ChatStreamEvent[] = []
  const answer = streamAnswer('cnv_1', 'Sweet peas?', { signal, onEvent: (e) => events.push(e) })
  return { answer, events }
}

const frame = (event: ChatStreamEvent) => `event: ${event.type}\ndata: ${JSON.stringify(event)}\n\n`

describe('streamAnswer', () => {
  it('asks for a stream and follows it to the saved answer, however it arrives', async () => {
    const stream = eventStream()
    const fetch = serve(stream)
    const saved = makeMessage({ content: 'Früh im März [1].', sources: [makeSource()] })
    const { answer, events } = ask()

    const bytes = new TextEncoder().encode(
      frame({ type: 'messageStart' }) +
        frame({ type: 'textDelta', text: 'Früh im März [1].' }) +
        frame({ type: 'messageEnd', message: saved }),
    )
    // Cut mid-frame and mid-character (between the two bytes of "ü"), as the network may.
    const cuts = [0, 7, 30, bytes.indexOf(0xc3) + 1, bytes.length].sort((a, b) => a - b)
    for (const [i, at] of cuts.slice(0, -1).entries()) stream.raw(bytes.slice(at, cuts[i + 1]))
    stream.end()

    await expect(answer).resolves.toEqual(saved)
    expect(events.map((e) => e.type)).toEqual(['messageStart', 'textDelta', 'messageEnd'])
    expect(events[1]).toEqual({ type: 'textDelta', text: 'Früh im März [1].' })
    const request = fetch.mock.calls[0]![0]
    expect(request.url).toMatch(/\/api\/v1\/conversations\/cnv_1\/messages$/)
    expect(request.headers.get('Accept')).toBe('text/event-stream')
    expect(await request.json()).toEqual({ content: 'Sweet peas?' })
  })

  it('fails with the problem of an error event', async () => {
    const stream = eventStream()
    serve(stream)
    const { answer } = ask()
    const failed = problem(502, 'Bad Gateway', 'No model.')

    stream.send({ type: 'messageStart' }, { type: 'error', problem: failed })
    stream.end()

    const error = await answer.catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).problem).toEqual(failed)
  })

  it('says the stream broke when it ends or drops before the answer is saved', async () => {
    const ended = eventStream()
    serve(ended)
    const first = ask()
    ended.send({ type: 'textDelta', text: 'You plan' })
    ended.end()
    await expect(first.answer).rejects.toBeInstanceOf(BrokenStreamError)

    const dropped = eventStream()
    serve(dropped)
    const second = ask()
    dropped.send({ type: 'textDelta', text: 'You plan' })
    dropped.fail(new TypeError('network error'))
    await expect(second.answer).rejects.toBeInstanceOf(BrokenStreamError)
  })

  it('passes on a question the server turns down', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => json(problem(409, 'Conflict', 'Full.'), 409)),
    )
    const { answer, events } = ask()

    const error = await answer.catch((e: unknown) => e)
    expect((error as ApiError).status).toBe(409)
    expect(events).toEqual([])
  })

  it('stops when called off, without taking the API for offline', async () => {
    const onOffline = vi.fn()
    configureApi({ token: () => null, onUnauthorized: () => {}, onOffline })
    const stream = eventStream()
    const fetch = serve(stream)
    const controller = new AbortController()
    const { answer, events } = ask(controller.signal)
    stream.send({ type: 'textDelta', text: 'You plan' })
    await vi.waitFor(() => expect(events).toHaveLength(1))
    expect(fetch).toHaveBeenCalledOnce()

    controller.abort()

    const error = await answer.catch((e: unknown) => e)
    expect((error as DOMException).name).toBe('AbortError')
    expect(onOffline).not.toHaveBeenCalled()
  })
})
