import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { ref } from 'vue'

import KDialog from '../KDialog.vue'
import KStatusChip from '../KStatusChip.vue'
import { englishMessages } from '../messages'
import { createCottage } from '../plugin'

describe('the message catalog', () => {
  it('speaks English without any setup', () => {
    const wrapper = mount(KStatusChip, { props: { status: 'ready' } })
    expect(wrapper.text()).toBe('Ready')
  })

  it('takes other words from createCottage', () => {
    const messages = {
      ...englishMessages,
      pageStatus: { ...englishMessages.pageStatus, ready: 'Fertig' },
    }
    const wrapper = mount(KStatusChip, {
      props: { status: 'ready' },
      global: { plugins: [createCottage({ messages })] },
    })
    expect(wrapper.text()).toBe('Fertig')
  })

  it('follows a ref, so a language switch shows up right away', async () => {
    const messages = ref(englishMessages)
    const wrapper = mount(KDialog, {
      props: { title: 'Rename', open: true },
      global: { plugins: [createCottage({ messages })] },
    })
    messages.value = { ...englishMessages, close: 'Schließen' }
    await wrapper.vm.$nextTick()
    expect(wrapper.find('button[aria-label="Schließen"]').exists()).toBe(true)
    wrapper.unmount()
  })

  it('falls back to English while the getter has nothing', () => {
    const wrapper = mount(KStatusChip, {
      props: { status: 'ready' },
      global: { plugins: [createCottage({ messages: () => undefined })] },
    })
    expect(wrapper.text()).toBe('Ready')
  })
})
