import { afterEach, describe, expect, it } from 'vitest'

import { ApiError } from '@/api/errors'
import { useConfirm } from '@/composables/useConfirm'
import { useToasts } from '@/ui'

const conflict = new ApiError({ type: 'about:blank', title: 'Conflict', status: 409 } as never)

afterEach(() => useToasts().clear())

describe('useConfirm', () => {
  it('asks about something and closes once it’s done', async () => {
    const del = useConfirm<{ name: string }>()
    del.ask({ name: 'Green notebook' })
    expect(del.open).toBe(true)
    let gone = ''
    await del.run(
      async (journal) => {
        gone = journal.name
      },
      { title: 'Couldn’t delete' },
    )
    expect(gone).toBe('Green notebook')
    expect(del.open).toBe(false)
    expect(del.busy).toBe(false)
  })

  it('stays open after a real error, so you can try again', async () => {
    const del = useConfirm()
    del.ask()
    await del.run(() => Promise.reject(new Error('boom')), { title: 'Couldn’t delete' })
    expect(del.open).toBe(true)
    expect(useToasts().items.value.at(-1)).toMatchObject({
      tone: 'error',
      title: 'Couldn’t delete',
    })
  })

  it('closes with a friendly toast for an expected status', async () => {
    const read = useConfirm()
    read.ask()
    await read.run(() => Promise.reject(conflict), {
      title: 'Couldn’t read it again',
      byStatus: { 409: { title: 'Already on it' } },
    })
    expect(read.open).toBe(false)
    expect(useToasts().items.value.at(-1)).toMatchObject({ tone: 'info', title: 'Already on it' })
  })
})
