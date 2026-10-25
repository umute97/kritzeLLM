import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import KCheckbox from '../KCheckbox.vue'
import KSearchField from '../KSearchField.vue'
import KSelect from '../KSelect.vue'
import KSwitch from '../KSwitch.vue'
import KTextArea from '../KTextArea.vue'
import KTextField from '../KTextField.vue'

describe('KTextField', () => {
  it('ties the label to the input and syncs v-model', async () => {
    const wrapper = mount(KTextField, {
      props: {
        label: 'Journal name',
        modelValue: 'Green',
        'onUpdate:modelValue': (v: string | number) => wrapper.setProps({ modelValue: v }),
      },
    })
    const input = wrapper.get('input')
    expect(wrapper.get('label').attributes('for')).toBe(input.attributes('id'))
    expect(input.element.value).toBe('Green')
    await input.setValue('Green notebook')
    expect(wrapper.props('modelValue')).toBe('Green notebook')
  })

  it('describes the input with its help, or its error instead', async () => {
    const wrapper = mount(KTextField, { props: { label: 'Name', help: 'Short is fine' } })
    const input = wrapper.get('input')
    expect(input.attributes('aria-describedby')).toMatch(/-help$/)
    expect(input.attributes('aria-invalid')).toBeUndefined()

    await wrapper.setProps({ error: 'Give it a name, even a tiny one' })
    expect(input.attributes('aria-invalid')).toBe('true')
    const describedby = input.attributes('aria-describedby')
    expect(describedby).toMatch(/-error$/)
    expect(wrapper.get(`#${describedby}`).text()).toContain('Give it a name')
    expect(wrapper.text()).not.toContain('Short is fine')
  })

  it('passes attributes to the input, not the wrapper', () => {
    const wrapper = mount(KTextField, { props: { label: 'Token' }, attrs: { autocomplete: 'off' } })
    expect(wrapper.get('input').attributes('autocomplete')).toBe('off')
  })

  it('lets you peek at a password', async () => {
    const wrapper = mount(KTextField, {
      props: { label: 'API token', type: 'password', revealable: true, modelValue: 'secret' },
    })
    expect(wrapper.get('input').attributes('type')).toBe('password')
    const eye = wrapper.get('button')
    expect(eye.attributes('aria-label')).toBe('Show API token')
    await eye.trigger('click')
    expect(wrapper.get('input').attributes('type')).toBe('text')
    expect(eye.attributes('aria-pressed')).toBe('true')
  })

  it('marks optional fields', () => {
    const wrapper = mount(KTextField, { props: { label: 'Description', optional: true } })
    expect(wrapper.get('label').text()).toContain('(optional)')
  })
})

describe('KTextArea', () => {
  it('syncs v-model', async () => {
    const wrapper = mount(KTextArea, {
      props: {
        label: 'Description',
        modelValue: '',
        'onUpdate:modelValue': (v: string) => wrapper.setProps({ modelValue: v }),
      },
    })
    await wrapper.get('textarea').setValue('What lives here')
    expect(wrapper.props('modelValue')).toBe('What lives here')
  })
})

describe('KSelect', () => {
  it('takes plain strings or options', async () => {
    const wrapper = mount(KSelect, {
      props: {
        label: 'Journal',
        options: ['All journals', { value: 'jrn_1', label: 'Green notebook' }],
        modelValue: 'All journals',
        'onUpdate:modelValue': (v: string) => wrapper.setProps({ modelValue: v }),
      },
    })
    const options = wrapper.findAll('option')
    expect(options.map((o) => o.text())).toEqual(['All journals', 'Green notebook'])
    await wrapper.get('select').setValue('jrn_1')
    expect(wrapper.props('modelValue')).toBe('jrn_1')
  })
})

describe('KSearchField', () => {
  it('searches on enter and clears with the little cross', async () => {
    const wrapper = mount(KSearchField, {
      props: {
        label: 'Search your pages',
        modelValue: 'sweet peas',
        'onUpdate:modelValue': (v: string) => wrapper.setProps({ modelValue: v }),
      },
    })
    await wrapper.get('input').trigger('keydown', { key: 'Enter' })
    expect(wrapper.emitted('search')).toEqual([['sweet peas']])

    await wrapper.get('button[aria-label="Clear search"]').trigger('click')
    expect(wrapper.props('modelValue')).toBe('')
    expect(wrapper.find('button[aria-label="Clear search"]').exists()).toBe(false)
  })
})

describe('KCheckbox', () => {
  it('is a labelled native checkbox', async () => {
    const wrapper = mount(KCheckbox, {
      props: {
        label: 'Remember this token on this device',
        modelValue: false,
        'onUpdate:modelValue': (v: boolean) => wrapper.setProps({ modelValue: v }),
      },
    })
    await wrapper.get('input[type="checkbox"]').setValue(true)
    expect(wrapper.props('modelValue')).toBe(true)
    expect(wrapper.get('label').text()).toContain('Remember this token')
  })
})

describe('KSwitch', () => {
  it('flips and says so', async () => {
    const wrapper = mount(KSwitch, {
      props: {
        label: 'Show scores',
        modelValue: false,
        'onUpdate:modelValue': (v: boolean) => wrapper.setProps({ modelValue: v }),
      },
    })
    const toggle = wrapper.get('[role="switch"]')
    expect(toggle.attributes('aria-checked')).toBe('false')
    await toggle.trigger('click')
    expect(wrapper.props('modelValue')).toBe(true)
    expect(toggle.attributes('aria-checked')).toBe('true')
    const labelId = toggle.attributes('aria-labelledby')
    expect(wrapper.get(`#${labelId}`).text()).toBe('Show scores')
  })
})
