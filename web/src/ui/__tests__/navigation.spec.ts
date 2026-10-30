import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { h } from 'vue'

import KBreadcrumb from '../KBreadcrumb.vue'
import KLoadMore from '../KLoadMore.vue'
import KNavLink from '../KNavLink.vue'
import KPageStepper from '../KPageStepper.vue'
import KProgressBar from '../KProgressBar.vue'
import KShelfPager from '../KShelfPager.vue'
import KTopNav from '../KTopNav.vue'

describe('KTopNav and KNavLink', () => {
  it('marks the current room and folds links behind a menu on phones', async () => {
    const wrapper = mount(KTopNav, {
      slots: {
        default: () => [
          h(KNavLink, { active: true, href: '#' }, () => 'Pages'),
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

describe('KShelfPager', () => {
  it('rests the arrows at the ends', async () => {
    const wrapper = mount(KShelfPager, {
      props: { range: 'Journals 1–4', canBack: false, canNext: true, noun: 'journals' },
    })
    const [back, next] = wrapper.findAll('button')
    expect(back!.attributes('aria-label')).toBe('Previous journals')
    expect(back!.attributes('disabled')).toBeDefined()
    expect(next!.attributes('disabled')).toBeUndefined()
    await next!.trigger('click')
    expect(wrapper.emitted('next')).toHaveLength(1)
  })
})

describe('KPageStepper', () => {
  it('steps between neighbouring pages', async () => {
    const wrapper = mount(KPageStepper, {
      props: {
        current: 12,
        total: 48,
        prevLabel: 'Page 11',
        nextLabel: 'Page 13',
        canPrev: true,
        canNext: false,
      },
    })
    expect(wrapper.text()).toContain('12 of 48')
    await wrapper.get('button[aria-label="Page 11"]').trigger('click')
    expect(wrapper.emitted('prev')).toHaveLength(1)
    expect(wrapper.get('button[aria-label="Page 13"]').attributes('disabled')).toBeDefined()
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
