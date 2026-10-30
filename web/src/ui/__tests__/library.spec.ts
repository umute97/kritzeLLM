import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import KBlockCard from '../KBlockCard.vue'
import KDropTarget from '../KDropTarget.vue'
import KFileButton from '../KFileButton.vue'
import KJournalCover from '../KJournalCover.vue'
import KPageCard from '../KPageCard.vue'
import KUploadRow from '../KUploadRow.vue'
import { tiltFor } from '../types'

describe('KJournalCover', () => {
  it('is a toggle that says which notebook is open', async () => {
    const wrapper = mount(KJournalCover, {
      props: { name: 'Green notebook', meta: '48 pages', selected: true },
    })
    expect(wrapper.attributes('aria-pressed')).toBe('true')
    expect(wrapper.text()).toContain('Green notebook')
    await wrapper.trigger('click')
    expect(wrapper.emitted('click')).toHaveLength(1)
  })

  it('reads in cream on the dark clay cover', () => {
    const wrapper = mount(KJournalCover, { props: { name: 'Travel journal', color: 'clay' } })
    expect(wrapper.find('.bg-clay').classes()).toContain('text-cream')
  })
})

describe('KPageCard', () => {
  it('links to the page with its number, date and status', () => {
    const wrapper = mount(KPageCard, {
      props: { pageNumber: 12, date: 'Mar 3', status: 'ready', imageUrl: 'blob:thumb' },
      attrs: { href: '/pages/pg_1' },
    })
    expect(wrapper.get('a').attributes('href')).toBe('/pages/pg_1')
    expect(wrapper.text()).toContain('Page 12')
    expect(wrapper.text()).toContain('Ready')
    expect(wrapper.get('img').attributes('alt')).toBe('')
  })

  it.each([
    ['uploaded', 'waiting…'],
    ['transcribing', 'reading…'],
  ] as const)('shows a little spinner while %s', (status, note) => {
    const wrapper = mount(KPageCard, { props: { pageNumber: 19, status } })
    expect(wrapper.text()).toContain(note)
  })

  it('offers a way out when reading failed, outside the link', async () => {
    const wrapper = mount(KPageCard, { props: { pageNumber: 18, status: 'failed' } })
    const retry = wrapper.findAll('button').find((b) => b.text() === 'Try again')!
    expect(retry.element.closest('a')).toBeNull()
    await retry.trigger('click')
    expect(wrapper.emitted('retry')).toHaveLength(1)
  })

  it('tilts gently by position', () => {
    expect([0, 1, 2, 3, 4].map(tiltFor)).toEqual([-1.5, 1, -0.5, 1.5, -1.5])
    const wrapper = mount(KPageCard, { props: { pageNumber: 1, status: 'ready', tilt: 1 } })
    expect(wrapper.attributes('style')).toContain('--tilt: 1deg')
  })
})

function fileList(...files: File[]) {
  return { files, items: files.map(() => ({})) }
}

const countLabel = (n: number) => (n === 1 ? '1 photo' : `${n} photos`)

describe('KDropTarget', () => {
  it('lays a hint over its content while dragging, then hands over the files', async () => {
    const wrapper = mount(KDropTarget, {
      props: { countLabel },
      slots: { default: '<p>Green notebook</p>' },
    })
    const photo = new File(['x'], 'IMG_2041.jpg', { type: 'image/jpeg' })
    await wrapper.trigger('dragenter', { dataTransfer: fileList(photo, photo) })
    expect(wrapper.text()).toContain('Let go to tuck them in')
    expect(wrapper.text()).toContain('2 photos')
    expect(wrapper.text()).toContain('Green notebook')
    await wrapper.trigger('drop', { dataTransfer: fileList(photo) })
    expect(wrapper.emitted('files')).toEqual([[[photo]]])
    expect(wrapper.text()).not.toContain('Let go to tuck them in')
  })

  it('only lets go of the hint when the drag leaves it entirely', async () => {
    const wrapper = mount(KDropTarget, { props: { countLabel } })
    const photo = new File(['x'], 'a.jpg', { type: 'image/jpeg' })
    await wrapper.trigger('dragenter', { dataTransfer: fileList(photo) })
    await wrapper.trigger('dragenter', { dataTransfer: fileList(photo) })
    await wrapper.trigger('dragleave')
    expect(wrapper.text()).toContain('Let go to tuck them in')
    await wrapper.trigger('dragleave')
    expect(wrapper.text()).not.toContain('Let go to tuck them in')
  })

  it('counts files in plain words without a count label', async () => {
    const wrapper = mount(KDropTarget)
    const file = new File(['x'], 'a.jpg', { type: 'image/jpeg' })
    await wrapper.trigger('dragenter', { dataTransfer: fileList(file, file) })
    expect(wrapper.text()).toContain('2 files')
  })

  it('ignores drops while disabled', async () => {
    const wrapper = mount(KDropTarget, { props: { disabled: true } })
    const file = new File(['x'], 'a.jpg', { type: 'image/jpeg' })
    await wrapper.trigger('dragenter', { dataTransfer: fileList(file) })
    expect(wrapper.text()).not.toContain('Let go to tuck them in')
    await wrapper.trigger('drop', { dataTransfer: fileList(file) })
    expect(wrapper.emitted('files')).toBeUndefined()
  })
})

describe('KFileButton', () => {
  it('hands over picked files and resets the input', async () => {
    const wrapper = mount(KFileButton, { slots: { default: 'Add photos' } })
    expect(wrapper.text()).toBe('Add photos')
    const input = wrapper.get('input[type="file"]')
    const photo = new File(['x'], 'IMG_2042.png', { type: 'image/png' })
    Object.defineProperty(input.element, 'files', { value: [photo], configurable: true })
    await input.trigger('change')
    expect(wrapper.emitted('files')).toEqual([[[photo]]])
    expect((input.element as HTMLInputElement).value).toBe('')
  })

  it('gives input attributes to the file input', () => {
    const wrapper = mount(KFileButton, { attrs: { capture: 'environment', class: 'flex-1' } })
    expect(wrapper.get('input[type="file"]').attributes('capture')).toBe('environment')
    expect(wrapper.classes()).toContain('flex-1')
  })

  it('can’t be used while disabled', () => {
    const wrapper = mount(KFileButton, { props: { disabled: true } })
    expect(wrapper.get('input').attributes('disabled')).toBeDefined()
    expect(wrapper.attributes('aria-disabled')).toBe('true')
  })
})

describe('KUploadRow', () => {
  it('follows the job and shows sending progress', () => {
    const wrapper = mount(KUploadRow, {
      props: { fileName: 'IMG_2045.heic', status: 'sending', progress: 62, note: '3.1 of 5 MB' },
    })
    expect(wrapper.text()).toContain('Sending')
    expect(wrapper.get('[role="progressbar"]').attributes('aria-valuenow')).toBe('62')
  })

  it('names duplicates and failures plainly', () => {
    expect(
      mount(KUploadRow, { props: { fileName: 'a.jpg', status: 'duplicate' } }).text(),
    ).toContain('Already here')
    const failed = mount(KUploadRow, {
      props: { fileName: 'big.png', status: 'failed', statusLabel: 'Too big' },
    })
    expect(failed.text()).toContain('Too big')
    expect(failed.classes()).toContain('bg-bark-soft')
    expect(mount(KUploadRow, { props: { fileName: 'c.jpg', status: 'deleted' } }).text()).toContain(
      'Deleted',
    )
  })
})

describe('KBlockCard', () => {
  function block(props: Record<string, unknown> = {}) {
    const wrapper = mount(KBlockCard, {
      props: {
        seq: 3,
        kind: 'list' as const,
        modelValue: '- buy twine',
        'onUpdate:modelValue': (v: string) => wrapper.setProps({ modelValue: v }),
        ...props,
      },
    })
    return wrapper
  }

  it('is labelled by its number and kind and edits its text', async () => {
    const wrapper = block()
    const textarea = wrapper.get('textarea')
    expect(textarea.attributes('aria-label')).toBe('Block 3, List')
    await textarea.setValue('- buy twine\n- call grandma')
    expect(wrapper.props('modelValue')).toBe('- buy twine\n- call grandma')
  })

  it('saves with cmd+enter and undoes with escape when changed', async () => {
    const wrapper = block({ dirty: true })
    expect(wrapper.text()).toContain('changed, not saved')
    const textarea = wrapper.get('textarea')
    await textarea.trigger('keydown', { key: 'Enter', metaKey: true })
    await textarea.trigger('keydown', { key: 'Escape' })
    expect(wrapper.emitted('save')).toHaveLength(1)
    expect(wrapper.emitted('undo')).toHaveLength(1)
  })

  it('ignores the shortcuts when nothing changed', async () => {
    const wrapper = block()
    await wrapper.get('textarea').trigger('keydown', { key: 'Enter', ctrlKey: true })
    expect(wrapper.emitted('save')).toBeUndefined()
  })

  it('asks to confirm unsure blocks', async () => {
    const wrapper = block({ uncertain: true })
    expect(wrapper.text()).toContain('not quite sure')
    await wrapper
      .findAll('button')
      .find((b) => b.text() === 'Looks right')!
      .trigger('click')
    expect(wrapper.emitted('confirm')).toHaveLength(1)
  })

  it('reports hover and focus so the page can point at it', async () => {
    const wrapper = block()
    await wrapper.trigger('mouseenter')
    await wrapper.trigger('mouseleave')
    expect(wrapper.emitted('activate')).toHaveLength(1)
    expect(wrapper.emitted('deactivate')).toHaveLength(1)
  })
})
