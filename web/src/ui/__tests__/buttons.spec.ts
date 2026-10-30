import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import KButton from '../KButton.vue'
import KIconButton from '../KIconButton.vue'

describe('KButton', () => {
  it('is a plain button that clicks', async () => {
    const wrapper = mount(KButton, { slots: { default: 'Save changes' } })
    const button = wrapper.get('button')
    expect(button.attributes('type')).toBe('button')
    expect(button.text()).toBe('Save changes')
    await button.trigger('click')
    expect(wrapper.emitted('click')).toHaveLength(1)
  })

  it('can submit a form', () => {
    const wrapper = mount(KButton, { props: { type: 'submit' } })
    expect(wrapper.get('button').attributes('type')).toBe('submit')
  })

  it('is disabled and busy while loading', () => {
    const wrapper = mount(KButton, { props: { loading: true }, slots: { default: 'Saving' } })
    const button = wrapper.get('button')
    expect(button.attributes('disabled')).toBeDefined()
    expect(button.attributes('aria-busy')).toBe('true')
    expect(button.find('svg').exists()).toBe(true)
  })

  it('renders as another element without button-only attributes', () => {
    const wrapper = mount(KButton, { props: { as: 'a', disabled: true }, attrs: { href: '/x' } })
    const link = wrapper.get('a')
    expect(link.attributes('href')).toBe('/x')
    expect(link.attributes('type')).toBeUndefined()
    expect(link.attributes('aria-disabled')).toBe('true')
  })

  it('keeps a disabled link from going anywhere', async () => {
    const wrapper = mount(KButton, { props: { as: 'a', disabled: true }, attrs: { href: '/x' } })
    const link = wrapper.get('a')
    expect(link.attributes('tabindex')).toBe('-1')
    const click = new MouseEvent('click', { bubbles: true, cancelable: true })
    link.element.dispatchEvent(click)
    expect(click.defaultPrevented).toBe(true)
  })

  it('lets an enabled link go', () => {
    const wrapper = mount(KButton, { props: { as: 'a' }, attrs: { href: '/x' } })
    const link = wrapper.get('a')
    expect(link.attributes('tabindex')).toBeUndefined()
    expect(link.attributes('aria-disabled')).toBeUndefined()
    const click = new MouseEvent('click', { bubbles: true, cancelable: true })
    link.element.dispatchEvent(click)
    expect(click.defaultPrevented).toBe(false)
  })

  it('looks dashed when disabled, whatever the variant', () => {
    const wrapper = mount(KButton, { props: { variant: 'danger', disabled: true } })
    expect(wrapper.classes()).toContain('border-dashed')
    expect(wrapper.classes()).not.toContain('bg-bark')
  })
})

describe('KIconButton', () => {
  it('is labelled for screen readers', () => {
    const wrapper = mount(KIconButton, { props: { icon: 'trash', label: 'Delete page' } })
    expect(wrapper.get('button').attributes('aria-label')).toBe('Delete page')
    expect(wrapper.get('svg').attributes('aria-hidden')).toBe('true')
  })

  it('only says pressed when it is a toggle', () => {
    const plain = mount(KIconButton, { props: { icon: 'menu', label: 'Menu' } })
    expect(plain.attributes('aria-pressed')).toBeUndefined()
    const toggle = mount(KIconButton, { props: { icon: 'eye', label: 'Show', pressed: false } })
    expect(toggle.attributes('aria-pressed')).toBe('false')
  })

  it('can submit a form', () => {
    const wrapper = mount(KIconButton, {
      props: { icon: 'arrow-up', label: 'Send', type: 'submit' },
    })
    expect(wrapper.get('button').attributes('type')).toBe('submit')
  })

  it('says it is disabled when it is a link', () => {
    const wrapper = mount(KIconButton, {
      props: { icon: 'close', label: 'Close', as: 'a', disabled: true },
    })
    expect(wrapper.get('a').attributes('aria-disabled')).toBe('true')
  })
})
