import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { nextTick } from 'vue'

import KBanner from '../KBanner.vue'
import KConfirmDialog from '../KConfirmDialog.vue'
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

  it('can take a richer title at another heading level', () => {
    const wrapper = mount(KDialog, {
      props: { title: 'Rename', open: true, headingLevel: 3 },
      slots: { title: 'Rename <em>Green notebook</em>' },
    })
    expect(wrapper.get('h3 em').text()).toBe('Green notebook')
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

  it('stays open when the click lands inside the card, padding included', async () => {
    const wrapper = mount(KDialog, {
      attachTo: document.body,
      props: { title: 'A new journal', open: true },
    })
    await wrapper.get('dialog > div').trigger('click')
    expect(wrapper.emitted('update:open')).toBeUndefined()
    wrapper.unmount()
  })

  it('submits from a footer button when it is a form', async () => {
    const wrapper = mount(KDialog, {
      attachTo: document.body,
      props: { title: 'Rename journal', open: true, form: true },
      slots: {
        default: '<input name="name" />',
        footer: '<button type="submit">Save</button>',
      },
    })
    const form = wrapper.get('dialog > form')
    expect(form.find('input').exists()).toBe(true)
    expect(form.find('button[type="submit"]').exists()).toBe(true)
    await form.trigger('submit')
    expect(wrapper.emitted('submit')).toHaveLength(1)
    wrapper.unmount()
  })

  it('keeps two form dialogs on one page apart', async () => {
    const make = (title: string) =>
      mount(KDialog, {
        attachTo: document.body,
        props: { title, open: false, form: true },
        slots: { footer: '<button type="submit">Save</button>' },
      })
    const first = make('A new journal')
    const second = make('Rename journal')
    await second.setProps({ open: true })
    await second.get('form').trigger('submit')
    expect(second.emitted('submit')).toHaveLength(1)
    expect(first.emitted('submit')).toBeUndefined()
    first.unmount()
    second.unmount()
  })

  it('holds on while it is not dismissible', async () => {
    const wrapper = mount(KDialog, {
      attachTo: document.body,
      props: { title: 'Saving', open: true, dismissible: false },
    })
    const dialog = wrapper.get('dialog')
    const cancel = new Event('cancel', { cancelable: true })
    dialog.element.dispatchEvent(cancel)
    expect(cancel.defaultPrevented).toBe(true)
    await dialog.trigger('click')
    expect(wrapper.get('button[aria-label="Close"]').attributes('disabled')).toBeDefined()
    expect(wrapper.emitted('update:open')).toBeUndefined()
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

describe('KMenu with its own trigger', () => {
  it('hands the trigger its menu-button wiring and gives focus back', async () => {
    const wrapper = mount(KMenu, {
      attachTo: document.body,
      props: { label: 'Journal actions', items },
      slots: {
        trigger: `<template #trigger="{ toggle, triggerProps }">
          <button v-bind="triggerProps" @click="toggle">Journal</button>
        </template>`,
      },
    })
    const trigger = wrapper.get('button[aria-haspopup="menu"]')
    expect(trigger.text()).toBe('Journal')
    expect(trigger.attributes('aria-expanded')).toBe('false')

    await trigger.trigger('click')
    await nextTick()
    const menu = wrapper.get('[role="menu"]')
    expect(trigger.attributes('aria-expanded')).toBe('true')
    expect(trigger.attributes('aria-controls')).toBe(menu.attributes('id'))

    await menu.trigger('keydown', { key: 'Escape' })
    expect(document.activeElement).toBe(trigger.element)
    wrapper.unmount()
  })
})

describe('KMenu items', () => {
  it('run their own action and explain why they are off', async () => {
    let renamed = false
    const wrapper = mount(KMenu, {
      attachTo: document.body,
      props: {
        label: 'Journal actions',
        items: [
          { id: 'rename', label: 'Rename journal', run: () => (renamed = true) },
          { id: 'delete', label: 'Delete journal', danger: true, disabled: true, hint: 'Busy' },
        ],
      },
    })
    await wrapper.get('button[aria-haspopup="menu"]').trigger('click')
    await nextTick()
    expect(wrapper.text()).toContain('Busy')
    await wrapper.findAll('[role="menuitem"]')[0]!.trigger('click')
    expect(renamed).toBe(true)
    expect(wrapper.emitted('select')).toEqual([['rename']])
    wrapper.unmount()
  })
})

describe('KConfirmDialog', () => {
  function confirm(props: Record<string, unknown> = {}) {
    const wrapper = mount(KConfirmDialog, {
      attachTo: document.body,
      props: {
        title: 'Delete Green notebook?',
        confirmLabel: 'Delete journal',
        open: true,
        'onUpdate:open': (v: boolean) => wrapper.setProps({ open: v }),
        ...props,
      },
    })
    return wrapper
  }

  it('asks, with the safe choice first and focused', async () => {
    const wrapper = confirm()
    const [keep, go] = wrapper.findAll('dialog button:not([aria-label])')
    expect(keep!.text()).toBe('Keep it')
    expect(keep!.attributes('autofocus')).toBeDefined()
    expect(go!.classes()).toContain('bg-bark')
    await go!.trigger('click')
    expect(wrapper.emitted('confirm')).toHaveLength(1)
    await keep!.trigger('click')
    expect(wrapper.props('open')).toBe(false)
    wrapper.unmount()
  })

  it('holds on while it works, and keeps its words while it closes', async () => {
    const wrapper = confirm({ loading: true })
    const cancel = new Event('cancel', { cancelable: true })
    wrapper.get('dialog').element.dispatchEvent(cancel)
    expect(cancel.defaultPrevented).toBe(true)

    await wrapper.setProps({ open: false, title: 'Delete undefined?', loading: false })
    expect(wrapper.get('h2').text()).toBe('Delete Green notebook?')
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
