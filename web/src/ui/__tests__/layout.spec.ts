import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import KCard from '../KCard.vue'
import KCardGrid from '../KCardGrid.vue'
import KEmptyState from '../KEmptyState.vue'
import KPageHeader from '../KPageHeader.vue'
import KPhoto from '../KPhoto.vue'
import KSection from '../KSection.vue'
import KSpinner from '../KSpinner.vue'

describe('KCard', () => {
  it('renders as anything, solid or dashed', () => {
    const form = mount(KCard, { props: { as: 'form' } })
    expect(form.element.tagName).toBe('FORM')
    expect(form.classes()).toContain('border-ink')
    expect(mount(KCard, { props: { variant: 'dashed' } }).classes()).toContain('border-dashed')
  })
})

describe('KSection', () => {
  it('is labelled by its own heading, twice on a page too', () => {
    const wrapper = mount({
      components: { KSection },
      template: `<div><KSection title="On the shelf" /><KSection title="Green notebook" /></div>`,
    })
    const sections = wrapper.findAll('section')
    const ids = sections.map((s) => s.attributes('aria-labelledby'))
    expect(new Set(ids).size).toBe(2)
    expect(wrapper.get(`#${ids[1]}`).text()).toBe('Green notebook')
  })

  it('puts its menu by the title and its aside across, on a card when framed', () => {
    const wrapper = mount(KSection, {
      props: { title: 'Green notebook', description: 'Garden notes', framed: true },
      slots: { 'title-after': '<button>⋯</button>', aside: '<span>3 done</span>' },
    })
    expect(wrapper.element.tagName).toBe('SECTION')
    expect(wrapper.classes()).toContain('rounded-card')
    expect(wrapper.get('h2').element.nextElementSibling?.textContent).toBe('⋯')
    expect(wrapper.text()).toContain('Garden notes')
    expect(wrapper.text()).toContain('3 done')
  })
})

describe('KPageHeader', () => {
  it('has the screen’s one h1, with its actions', () => {
    const wrapper = mount(KPageHeader, {
      props: { title: 'Your journals', subtitle: 'pick a notebook' },
      slots: { actions: '<button>New journal</button>' },
    })
    expect(wrapper.get('h1').text()).toBe('Your journals')
    expect(wrapper.text()).toContain('pick a notebook')
    expect(wrapper.get('button').text()).toBe('New journal')
  })
})

describe('KCardGrid', () => {
  it('stands in with skeletons of the right shape while loading', () => {
    const covers = mount(KCardGrid, { props: { kind: 'covers', loading: true, skeletons: 3 } })
    expect(covers.findAll('li')).toHaveLength(3)
    expect(covers.get('li span').classes()).toContain('h-[132px]')
    expect(covers.attributes('aria-busy')).toBe('true')

    const pages = mount(KCardGrid, {
      props: { kind: 'pages' },
      slots: { default: '<li>Page 1</li>' },
    })
    expect(pages.text()).toBe('Page 1')
  })
})

describe('KPhoto', () => {
  it('shows the photo in its own shape', () => {
    const wrapper = mount(KPhoto, {
      props: { src: 'blob:photo', alt: 'Page 3', width: 3, height: 4, fit: 'contain' },
    })
    expect(wrapper.get('img').attributes('alt')).toBe('Page 3')
    expect(wrapper.get('img').classes()).toContain('object-contain')
    expect(wrapper.attributes('style')).toContain('aspect-ratio: 3 / 4')
  })

  it('is lined paper until then, with words or a daisy on it', () => {
    const excerpt = mount(KPhoto, { slots: { default: 'Sweet peas went in' } })
    expect(excerpt.find('img').exists()).toBe(false)
    expect(excerpt.find('.paper-lines').text()).toBe('Sweet peas went in')

    const loading = mount(KPhoto, { props: { loadingLabel: 'Loading the photo' } })
    expect(loading.get('[role="status"]').attributes('aria-label')).toBe('Loading the photo')
  })
})

describe('little helpers', () => {
  it('KEmptyState draws its doodle, KSpinner can fill a band', () => {
    expect(
      mount(KEmptyState, { props: { title: 'Nothing', doodle: 'squiggle' } })
        .find('svg')
        .exists(),
    ).toBe(true)
    expect(mount(KSpinner, { props: { block: true } }).classes()).toContain('justify-center')
  })
})
