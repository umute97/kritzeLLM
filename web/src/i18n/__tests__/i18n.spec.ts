import { afterEach, describe, expect, it, vi } from 'vitest'

import { i18n, pickLocale, setLocale } from '@/i18n'

afterEach(() => {
  setLocale('en')
  localStorage.clear()
  vi.unstubAllGlobals()
})

function browserSpeaks(...languages: string[]) {
  vi.stubGlobal('navigator', { ...navigator, languages })
}

describe('picking a language', () => {
  it('follows the browser’s first language we speak', () => {
    browserSpeaks('de-AT', 'en')
    expect(pickLocale()).toBe('de')
    browserSpeaks('fr-FR', 'en-GB')
    expect(pickLocale()).toBe('en')
    browserSpeaks('ja')
    expect(pickLocale()).toBe('en')
  })

  it('prefers the one picked before', () => {
    browserSpeaks('en-US')
    setLocale('de')
    expect(localStorage.getItem('kritzellm.locale')).toBe('de')
    expect(pickLocale()).toBe('de')
  })

  it('switches the words and the page’s lang', () => {
    setLocale('de')
    expect(document.documentElement.lang).toBe('de')
    expect(i18n.global.t('counts.pages', 1)).toBe('1 Seite')
    expect(i18n.global.t('counts.pages', 3)).toBe('3 Seiten')
    setLocale('en')
    expect(i18n.global.t('counts.pages', 0)).toBe('0 pages')
    expect(i18n.global.t('uploads.failed', 1)).toBe('1 needs a hand')
  })
})
