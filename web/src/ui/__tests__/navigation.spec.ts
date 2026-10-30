import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { h } from 'vue'

import KBreadcrumb from '../KBreadcrumb.vue'
import KLoadMore from '../KLoadMore.vue'
import KNavLink from '../KNavLink.vue'
import KPager from '../KPager.vue'
import KProgressBar from '../KProgressBar.vue'
import KTopNav from '../KTopNav.vue'

describe('KTopNav and KNavLink', () => {
  it('marks the current room and folds links behind a menu on phones', async () => {
    const wrapper = mount(KTopNav, {
      slots: {
        default: () => [
          h(KNavLink, { current: true, href: '#' }, () => 'Pages'),
          h(KNavLink, { href: '#' }, () => 'Search'),
        ],
        end: 'hi there',
      },
    })
    const links = wrapper.findAll('a')
    expect(links[0]!.attributes('aria-current')).toBe('page')
    expect(links[1]!.attributes('aria-current')).toBeUndefined()

    const menu = wrapper.get('button[aria-label="Menu"]')
    const panel = wrapper.get(`#${menu.attributes('aria-controls')}`)
    expect(panel.classes()).toContain('hidden')
    await menu.trigger('click')
    expect(menu.attributes('aria-expanded')).toBe('true')
    expect(panel.classes()).not.toContain('hidden')
  })
})

describe('KNavLink badge', () => {
  it('reads out the badge label instead of the bare number', () => {
    const wrapper = mount(KNavLink, {
      props: { href: '#', badge: 3, badgeLabel: '3 pages need a hand' },
      slots: { default: 'Pages' },
    })
    expect(wrapper.get('.sr-only').text()).toBe('3 pages need a hand')
    expect(wrapper.get('[aria-hidden="true"]').text()).toBe('3')
  })
})

describe('KBreadcrumb', () => {
  it('links the way back and marks where you are', () => {
    const wrapper = mount(KBreadcrumb, {
      props: {
        items: [
          { label: 'Journals', to: '/' },
          { label: 'Green notebook', to: '/journals/jrn_1' },
          { label: 'Page 12' },
        ],
      },
    })
    expect(wrapper.findAll('a').map((a) => a.attributes('href'))).toEqual(['/', '/journals/jrn_1'])
    expect(wrapper.get('[aria-current="page"]').text()).toBe('Page 12')
  })
})

describe('KPager', () => {
  it('steps between neighbours around what it says', async () => {
    const wrapper = mount(KPager, {
      props: { prevLabel: 'Page 11', nextLabel: 'Page 13', canPrev: true, canNext: false },
      slots: { default: '<span>12 of 48</span>' },
    })
    const [prev, middle, next] = wrapper.element.children
    expect(prev!.getAttribute('aria-label')).toBe('Page 11')
    expect(middle!.textContent).toBe('12 of 48')
    expect(next!.getAttribute('disabled')).not.toBeNull()
    await wrapper.get('button[aria-label="Page 11"]').trigger('click')
    expect(wrapper.emitted('prev')).toHaveLength(1)
  })

  it('can say where you are before the arrows', async () => {
    const wrapper = mount(KPager, {
      props: {
        prevLabel: 'Previous journals',
        nextLabel: 'More journals',
        canPrev: false,
        canNext: true,
        textFirst: true,
      },
      slots: { default: '<span>Journals 1–4</span>' },
    })
    expect(wrapper.element.firstElementChild!.textContent).toBe('Journals 1–4')
    expect(
      wrapper.get('button[aria-label="Previous journals"]').attributes('disabled'),
    ).toBeDefined()
    await wrapper.get('button[aria-label="More journals"]').trigger('click')
    expect(wrapper.emitted('next')).toHaveLength(1)
  })
})

describe('KProgressBar as a meter', () => {
  it('measures instead of counting down', () => {
    const wrapper = mount(KProgressBar, {
      props: { value: 0.5, max: 1, label: 'Words score', meter: true, color: 'lemon' },
    })
    expect(wrapper.attributes('role')).toBe('meter')
    expect(wrapper.find('.bg-lemon').attributes('style')).toContain('width: 50%')
  })
})

describe('KLoadMore', () => {
  it('offers more only while there is more', async () => {
    const wrapper = mount(KLoadMore, {
      props: { summary: 'Showing 8 of 48 pages', hasMore: true, label: 'Show more pages' },
    })
    await wrapper.get('button').trigger('click')
    expect(wrapper.emitted('more')).toHaveLength(1)
    await wrapper.setProps({ hasMore: false, summary: 'All 48 pages' })
    expect(wrapper.find('button').exists()).toBe(false)
    expect(wrapper.text()).toBe('All 48 pages')
  })
})

describe('KProgressBar', () => {
  it('fills to the share done and clamps', async () => {
    const wrapper = mount(KProgressBar, { props: { value: 3, max: 6, label: 'Upload' } })
    expect(wrapper.attributes('aria-valuenow')).toBe('3')
    const fill = () => wrapper.get('[role="progressbar"] > div').attributes('style')
    expect(fill()).toContain('width: 50%')
    await wrapper.setProps({ value: 9 })
    expect(fill()).toContain('width: 100%')
  })
})
