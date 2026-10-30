import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { ref } from 'vue'

import KDialog from '../KDialog.vue'
import KStatusChip from '../KStatusChip.vue'
import { englishMessages, mergeMessages } from '../messages'
import { createCottage } from '../plugin'

describe('the message catalog', () => {
  it('speaks English without any setup', () => {
    const wrapper = mount(KStatusChip, { props: { status: 'ready' } })
    expect(wrapper.text()).toBe('Ready')
  })

  it('takes other words from createCottage, one entry of a group at a time', () => {
    const wrapper = mount(KStatusChip, {
      props: { status: 'ready' },
      global: { plugins: [createCottage({ messages: { pageStatus: { ready: 'Fertig' } } })] },
    })
    expect(wrapper.text()).toBe('Fertig')
  })

  it('follows a ref, so a language switch shows up right away', async () => {
    const messages = ref({ close: 'Close' })
    const wrapper = mount(KDialog, {
      props: { title: 'Rename', open: true },
      global: { plugins: [createCottage({ messages })] },
    })
    messages.value = { close: 'Schließen' }
    await wrapper.vm.$nextTick()
    expect(wrapper.find('button[aria-label="Schließen"]').exists()).toBe(true)
    wrapper.unmount()
  })

  it('keeps the rest of a group when one entry changes', () => {
    const merged = mergeMessages(englishMessages, { jobStatus: { queued: 'Wartet' } })
    expect(merged.jobStatus).toEqual({ ...englishMessages.jobStatus, queued: 'Wartet' })
    expect(merged.close).toBe('Close')
  })
})
