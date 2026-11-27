import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import KCitationChip from '../KCitationChip.vue'
import KComposer from '../KComposer.vue'
import KHighlight from '../KHighlight.vue'
import KMessage from '../KMessage.vue'
import KSearchResult from '../KSearchResult.vue'
import KSourceCard from '../KSourceCard.vue'
import KToolActivity from '../KToolActivity.vue'
import type { Quote } from '../types'

describe('KComposer', () => {
  function composer(props: Record<string, unknown> = {}) {
    const wrapper = mount(KComposer, {
      props: {
        label: 'Ask your journal',
        modelValue: '',
        'onUpdate:modelValue': (v: string) => wrapper.setProps({ modelValue: v }),
        ...props,
      },
    })
    return wrapper
  }

  it('sends on enter, not on shift+enter, and never empty', async () => {
    const wrapper = composer()
    const textarea = wrapper.get('textarea')
    expect(wrapper.get('button[aria-label="Send"]').attributes('disabled')).toBeDefined()
    await textarea.trigger('keydown', { key: 'Enter' })
    expect(wrapper.emitted('send')).toBeUndefined()

    await textarea.setValue('  When did I plant the sweet peas?  ')
    await textarea.trigger('keydown', { key: 'Enter', shiftKey: true })
    expect(wrapper.emitted('send')).toBeUndefined()
    await textarea.trigger('keydown', { key: 'Enter' })
    expect(wrapper.emitted('send')).toEqual([['When did I plant the sweet peas?']])
  })

  it('turns send into stop while streaming', async () => {
    const wrapper = composer({ modelValue: 'Did they bloom?', streaming: true })
    expect(wrapper.find('button[aria-label="Send"]').exists()).toBe(false)
    await wrapper.get('button').trigger('click')
    expect(wrapper.emitted('stop')).toHaveLength(1)
    await wrapper.get('textarea').trigger('keydown', { key: 'Enter' })
    expect(wrapper.emitted('send')).toBeUndefined()
  })
})

describe('KMessage', () => {
  it('shows a caret while streaming and raises an alert when it broke off', () => {
    const streaming = mount(KMessage, {
      props: { author: 'assistant', streaming: true },
      slots: { default: 'They bloomed in late May' },
    })
    expect(streaming.find('.animate-blink').exists()).toBe(true)
    expect(streaming.find('[aria-live="polite"]').exists()).toBe(true)

    const broken = mount(KMessage, {
      props: { author: 'assistant', error: true },
      slots: { default: 'The answer stopped halfway.', actions: '<button>Ask again</button>' },
    })
    expect(broken.attributes('role')).toBe('alert')
    expect(broken.text()).toContain('Ask again')
  })

  it('puts your own messages on the right', () => {
    const mine = mount(KMessage, { props: { author: 'user' }, slots: { default: 'Hi' } })
    expect(mine.classes()).toContain('self-end')
  })
})

describe('KToolActivity', () => {
  it('unfolds the steps once done', async () => {
    const wrapper = mount(KToolActivity, {
      props: { state: 'done', expanded: false },
      slots: { default: 'searched twice, read 4 pages' },
    })
    const button = wrapper.get('button')
    expect(button.attributes('aria-expanded')).toBe('false')
    await button.trigger('click')
    expect(wrapper.emitted('toggle')).toHaveLength(1)
  })

  it('is a plain line while working', () => {
    const wrapper = mount(KToolActivity, {
      props: { state: 'working', icon: 'book' },
      slots: { default: 'reading page 14…' },
    })
    expect(wrapper.find('button').exists()).toBe(false)
    expect(wrapper.text()).toBe('reading page 14…')
  })
})

describe('KCitationChip and KSourceCard', () => {
  it('press the chip that is shown in Sources', () => {
    expect(
      mount(KCitationChip, { props: { label: 'p. 12', selected: true } }).attributes(
        'aria-pressed',
      ),
    ).toBe('true')
    expect(mount(KCitationChip, { props: { label: 'p. 14' } }).attributes('aria-pressed')).toBe(
      'false',
    )
  })

  it('quotes the source with the cited words marked and links to the page', () => {
    const wrapper = mount(KSourceCard, {
      props: {
        title: 'Page 12',
        date: 'Mar 3',
        before: 'and ',
        quote: 'I finally planted the sweet peas',
        after: ' by the fence.',
        to: '/pages/pg_1',
      },
    })
    expect(wrapper.get('mark').text()).toBe('I finally planted the sweet peas')
    expect(wrapper.get('a').attributes('href')).toBe('/pages/pg_1')
  })
})

describe('KHighlight', () => {
  it('marks every stretch it is given', () => {
    const wrapper = mount(KHighlight, {
      props: {
        text: 'sweet peas, basil and more sweet peas',
        marks: [
          [0, 10],
          [27, 37],
        ],
      },
    })
    expect(wrapper.text()).toBe('sweet peas, basil and more sweet peas')
    expect(wrapper.findAll('mark').map((m) => m.text())).toEqual(['sweet peas', 'sweet peas'])
  })
})

describe('KSearchResult', () => {
  const quotes: Quote[] = [
    { kind: 'heading', text: 'Saturday' },
    { kind: 'paragraph', text: 'I finally planted the sweet peas.', marks: [[22, 32]] },
  ]

  it('quotes every matched block with its kind, and says how many more matched', async () => {
    const wrapper = mount(KSearchResult, {
      props: { pageNumber: 12, journal: 'Green notebook', date: 'Mar 3', quotes },
    })
    expect(wrapper.text()).toContain('Green notebook · Mar 3')
    expect(wrapper.text()).toContain('Heading')
    expect(wrapper.text()).toContain('Paragraph')
    expect(wrapper.text()).toContain('Saturday')
    expect(wrapper.get('mark').text()).toBe('sweet peas')
    expect(wrapper.text()).not.toContain('more block')

    await wrapper.setProps({ more: 2 })
    expect(wrapper.text()).toContain('and 2 more blocks')
  })
})
