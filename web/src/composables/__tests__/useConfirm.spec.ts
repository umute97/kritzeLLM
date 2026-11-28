import { describe, expect, it } from 'vitest'

import { ApiError } from '@/api/errors'
import { useConfirm } from '@/composables/useConfirm'
import { problem } from '@/test-utils'
import { useToasts } from '@/ui'

const conflict = new ApiError(problem(409, 'Conflict'))

describe('useConfirm', () => {
  it('asks about something and closes once it’s done', async () => {
    let gone = ''
    const del = useConfirm(
      async (journal: { name: string }) => {
        gone = journal.name
      },
      () => ({ title: 'Couldn’t delete' }),
    )
    del.ask({ name: 'Green notebook' })
    expect(del.open).toBe(true)
    await del.run()
    expect(gone).toBe('Green notebook')
    expect(del.open).toBe(false)
    expect(del.busy).toBe(false)
  })

  it('stays open after a real error, so you can try again', async () => {
    const del = useConfirm(
      () => Promise.reject(new Error('boom')),
      () => ({ title: 'Couldn’t delete' }),
    )
    del.ask()
    await del.run()
    expect(del.open).toBe(true)
    expect(useToasts().items.value.at(-1)).toMatchObject({
      tone: 'error',
      title: 'Couldn’t delete',
    })
  })

  it('closes with a friendly toast for an expected status', async () => {
    const read = useConfirm(
      () => Promise.reject(conflict),
      () => ({
        title: 'Couldn’t read it again',
        byStatus: { 409: { title: 'Already on it' } },
      }),
    )
    read.ask()
    await read.run()
    expect(read.open).toBe(false)
    expect(useToasts().items.value.at(-1)).toMatchObject({ tone: 'info', title: 'Already on it' })
  })

  it('runs once at a time', async () => {
    let runs = 0
    const del = useConfirm(
      async () => {
        runs++
      },
      () => ({ title: 'Couldn’t delete' }),
    )
    del.ask()
    await Promise.all([del.run(), del.run()])
    expect(runs).toBe(1)
  })
})
