import { mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'

import KToast from '../KToast.vue'
import KToastStack from '../KToastStack.vue'
import { AUTO_DISMISS_MS, useToasts } from '../toasts'

const toasts = useToasts()

beforeEach(() => {
  vi.useFakeTimers()
})

afterEach(() => {
  toasts.clear()
  vi.useRealTimers()
})

describe('useToasts', () => {
  it('lets happy toasts float away on their own', () => {
    toasts.push({ tone: 'success', title: 'Pages tucked in' })
    expect(toasts.items.value).toHaveLength(1)
    vi.advanceTimersByTime(AUTO_DISMISS_MS)
    expect(toasts.items.value).toHaveLength(0)
  })

  it('keeps errors and warnings until dismissed', () => {
    const id = toasts.push({ tone: 'error', title: 'Couldn’t save block 3' })
    toasts.push({ tone: 'warning', title: 'Lost the connection' })
    vi.advanceTimersByTime(AUTO_DISMISS_MS * 10)
    expect(toasts.items.value).toHaveLength(2)
    toasts.dismiss(id)
    expect(toasts.items.value.map((t) => t.title)).toEqual(['Lost the connection'])
  })

  it('holds a toast while paused', () => {
    const id = toasts.push({ tone: 'info', title: 'Already in this journal' })
    toasts.pause(id)
    vi.advanceTimersByTime(AUTO_DISMISS_MS * 2)
    expect(toasts.items.value).toHaveLength(1)
    toasts.resume(id)
    vi.advanceTimersByTime(AUTO_DISMISS_MS)
    expect(toasts.items.value).toHaveLength(0)
  })

  it('turns a loading toast into a happy one that then leaves', () => {
    const id = toasts.push({ tone: 'loading', title: 'Uploading', progress: { value: 1, max: 6 } })
    vi.advanceTimersByTime(AUTO_DISMISS_MS * 2)
    toasts.update(id, { tone: 'success', title: 'Pages tucked in', progress: undefined })
    expect(toasts.items.value[0]?.title).toBe('Pages tucked in')
    vi.advanceTimersByTime(AUTO_DISMISS_MS)
    expect(toasts.items.value).toHaveLength(0)
  })
})

describe('KToast', () => {
  it('raises an alert for errors and hides details until asked', async () => {
    const wrapper = mount(KToast, {
      props: { tone: 'error', title: 'Couldn’t save', technical: '409 Conflict' },
    })
    expect(wrapper.attributes('role')).toBe('alert')
    expect(wrapper.find('code').exists()).toBe(false)
    const toggle = wrapper.get('button[aria-expanded]')
    await toggle.trigger('click')
    expect(wrapper.get('code').text()).toBe('409 Conflict')
    expect(toggle.text()).toBe('Hide details')
  })

  it('takes an icon that says it better than its tone', () => {
    const plain = mount(KToast, { props: { tone: 'warning', title: 'Already reading' } })
    const custom = mount(KToast, {
      props: { tone: 'warning', title: 'Lost the connection', icon: 'reconnect' },
    })
    expect(plain.get('svg path').attributes('d')).not.toBe(custom.get('svg path').attributes('d'))
  })

  it('is a polite status otherwise, with a working dismiss and action', async () => {
    const wrapper = mount(KToast, {
      props: { tone: 'warning', title: 'Lost the connection', actionLabel: 'Try now' },
    })
    expect(wrapper.attributes('role')).toBe('status')
    await wrapper.get('button[aria-label="Dismiss"]').trigger('click')
    await wrapper
      .findAll('button')
      .find((b) => b.text() === 'Try now')!
      .trigger('click')
    expect(wrapper.emitted('dismiss')).toHaveLength(1)
    expect(wrapper.emitted('action')).toHaveLength(1)
  })

  it('can’t be dismissed while loading', () => {
    const wrapper = mount(KToast, {
      props: { tone: 'loading', title: 'Uploading', progress: { value: 4, max: 6 } },
    })
    expect(wrapper.find('button[aria-label="Dismiss"]').exists()).toBe(false)
    expect(wrapper.get('[role="progressbar"]').attributes('aria-valuenow')).toBe('4')
    expect(wrapper.text()).toContain('4 of 6')
  })
})

describe('KToastStack', () => {
  it('shows the three newest and dismisses from the stack', async () => {
    const wrapper = mount(KToastStack)
    for (const title of ['one', 'two', 'three', 'four']) toasts.push({ tone: 'error', title })
    await nextTick()
    expect(wrapper.findAll('strong').map((s) => s.text())).toEqual(['two', 'three', 'four'])

    await wrapper.findAll('button[aria-label="Dismiss"]')[0]!.trigger('click')
    expect(toasts.items.value.map((t) => t.title)).toEqual(['one', 'three', 'four'])
  })
})
