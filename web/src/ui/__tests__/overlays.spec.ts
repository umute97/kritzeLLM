import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { nextTick } from 'vue'

import KBanner from '../KBanner.vue'
import KDialog from '../KDialog.vue'
import KMenu from '../KMenu.vue'
import KTooltip from '../KTooltip.vue'

describe('KDialog', () => {
  it('opens as a modal, is labelled, and closes with its button', async () => {
    const wrapper = mount(KDialog, {
      attachTo: document.body,
      props: {
        title: 'Delete page 18?',
        description: 'This can’t be undone.',
        open: false,
        'onUpdate:open': (v: boolean) => wrapper.setProps({ open: v }),
      },
      slots: { footer: '<button>Keep it</button>' },
    })
    const dialog = wrapper.get('dialog')
    expect((dialog.element as HTMLDialogElement).open).toBe(false)

    await wrapper.setProps({ open: true })
    expect((dialog.element as HTMLDialogElement).open).toBe(true)
    expect(wrapper.get(`#${dialog.attributes('aria-labelledby')}`).text()).toBe('Delete page 18?')
    expect(wrapper.get(`#${dialog.attributes('aria-describedby')}`).text()).toContain('undone')

    await wrapper.get('button[aria-label="Close"]').trigger('click')
    expect(wrapper.props('open')).toBe(false)
    expect((dialog.element as HTMLDialogElement).open).toBe(false)
    wrapper.unmount()
  })

  it('closes when the backdrop is clicked', async () => {
    const wrapper = mount(KDialog, {
      attachTo: document.body,
      props: { title: 'A new journal', open: true },
    })
    await wrapper.get('dialog').trigger('click')
    expect(wrapper.emitted('update:open')).toEqual([[false]])
    wrapper.unmount()
  })
})

const items = [
  { id: 'open', label: 'Open page' },
  { id: 'retranscribe', label: 'Re-transcribe' },
  { id: 'delete', label: 'Delete page', danger: true },
]

describe('KMenu', () => {
  it('opens, focuses the first item and picks one', async () => {
    const wrapper = mount(KMenu, {
      attachTo: document.body,
      props: { label: 'Page actions', items },
    })
    const trigger = wrapper.get('button[aria-haspopup="menu"]')
    expect(trigger.attributes('aria-expanded')).toBe('false')

    await trigger.trigger('click')
    await nextTick()
    const menuitems = wrapper.findAll('[role="menuitem"]')
    expect(menuitems.map((m) => m.text())).toEqual(['Open page', 'Re-transcribe', 'Delete page'])
    expect(document.activeElement).toBe(menuitems[0]!.element)
    expect(wrapper.find('[aria-hidden="true"].h-px').exists()).toBe(true)

    await menuitems[1]!.trigger('click')
    expect(wrapper.emitted('select')).toEqual([['retranscribe']])
    expect(wrapper.find('[role="menu"]').exists()).toBe(false)
    wrapper.unmount()
  })

  it('moves with the arrow keys and closes on escape', async () => {
    const wrapper = mount(KMenu, {
      attachTo: document.body,
      props: { label: 'Page actions', items },
    })
    await wrapper.get('button[aria-haspopup="menu"]').trigger('click')
    await nextTick()
    const menu = wrapper.get('[role="menu"]')
    await menu.trigger('keydown', { key: 'ArrowUp' })
    expect(document.activeElement?.textContent).toContain('Delete page')
    await menu.trigger('keydown', { key: 'Escape' })
    expect(wrapper.find('[role="menu"]').exists()).toBe(false)
    expect(document.activeElement).toBe(wrapper.get('button[aria-haspopup="menu"]').element)
    wrapper.unmount()
  })
})

describe('KTooltip', () => {
  it('shows on focus and describes its trigger', async () => {
    const wrapper = mount(KTooltip, {
      attachTo: document.body,
      props: { text: 'Read this page again' },
      slots: {
        default: `<template #default="{ describedby }"><button :aria-describedby="describedby">↻</button></template>`,
      },
    })
    const tip = wrapper.get('[role="tooltip"]')
    expect(tip.isVisible()).toBe(false)
    expect(wrapper.get('button').attributes('aria-describedby')).toBe(tip.attributes('id'))
    await wrapper.trigger('focusin')
    expect(tip.isVisible()).toBe(true)
    wrapper.unmount()
  })
})

describe('KBanner', () => {
  it('raises an alert for errors and a status for info', () => {
    expect(
      mount(KBanner, { props: { title: 'The cottage door is shut' } }).attributes('role'),
    ).toBe('alert')
    expect(mount(KBanner, { props: { title: 'Note', tone: 'info' } }).attributes('role')).toBe(
      'status',
    )
  })
})
