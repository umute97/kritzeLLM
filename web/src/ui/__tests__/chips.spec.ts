import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import KBlockKindTag from '../KBlockKindTag.vue'
import KFilterChips from '../KFilterChips.vue'
import KFlag from '../KFlag.vue'
import KSegmented from '../KSegmented.vue'
import KStatusChip from '../KStatusChip.vue'

describe('KStatusChip', () => {
  it.each([
    ['uploaded', 'Uploaded', 'bg-paper'],
    ['transcribing', 'Transcribing', 'bg-lemon-soft'],
    ['indexing', 'Indexing', 'bg-orchid-soft'],
    ['ready', 'Ready', 'bg-herb-soft'],
    ['failed', 'Failed', 'bg-bark'],
  ] as const)('says %s in words and colour', (status, label, ground) => {
    const wrapper = mount(KStatusChip, { props: { status } })
    expect(wrapper.text()).toBe(label)
    expect(wrapper.classes()).toContain(ground)
  })

  it('speaks job status too, and takes a custom label', () => {
    expect(mount(KStatusChip, { props: { kind: 'job', status: 'queued' } }).text()).toBe('Waiting')
    expect(mount(KStatusChip, { props: { kind: 'job', status: 'succeeded' } }).text()).toBe('Done')
    expect(mount(KStatusChip, { props: { status: 'failed', label: 'Too big' } }).text()).toBe(
      'Too big',
    )
  })
})

describe('KBlockKindTag and KFlag', () => {
  it('name block kinds and flags', () => {
    expect(mount(KBlockKindTag, { props: { kind: 'marginNote' } }).text()).toContain('Margin note')
    expect(mount(KFlag, { props: { kind: 'unsure' } }).text()).toBe('not quite sure')
    expect(mount(KFlag, { props: { kind: 'duplicate' } }).text()).toBe('already here')
  })
})

const filters = [
  { value: 'all', label: 'All' },
  { value: 'ready', label: 'Ready' },
  { value: 'failed', label: 'Needs a hand' },
] as const

describe('KFilterChips', () => {
  it('marks the picked chip with a tick and aria-pressed', async () => {
    const wrapper = mount(KFilterChips, {
      props: {
        label: 'Filter pages',
        options: [...filters],
        modelValue: 'all',
        'onUpdate:modelValue': (v: string) => wrapper.setProps({ modelValue: v }),
      },
    })
    expect(wrapper.get('[role="group"]').attributes('aria-label')).toBe('Filter pages')
    const buttons = wrapper.findAll('button')
    expect(buttons.map((b) => b.attributes('aria-pressed'))).toEqual(['true', 'false', 'false'])
    expect(buttons[0]!.find('svg').exists()).toBe(true)

    await buttons[2]!.trigger('click')
    expect(wrapper.props('modelValue')).toBe('failed')
    expect(wrapper.findAll('button').map((b) => b.attributes('aria-pressed'))).toEqual([
      'false',
      'false',
      'true',
    ])
  })
})

describe('KSegmented', () => {
  it('switches views', async () => {
    const wrapper = mount(KSegmented, {
      props: {
        label: 'Show',
        options: [
          { value: 'photo', label: 'Photo' },
          { value: 'both', label: 'Both' },
        ],
        modelValue: 'both',
        'onUpdate:modelValue': (v: string) => wrapper.setProps({ modelValue: v }),
      },
    })
    await wrapper.get('button').trigger('click')
    expect(wrapper.props('modelValue')).toBe('photo')
  })
})
