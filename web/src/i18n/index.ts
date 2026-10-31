import { createI18n } from 'vue-i18n'

import { de } from './de'
import { en, type Messages } from './en'
import { uiGerman } from './ui.de'

declare module 'vue-i18n' {
  // eslint-disable-next-line @typescript-eslint/no-empty-object-type
  export interface DefineLocaleMessage extends Messages {}
}

export const locales = ['en', 'de'] as const
export type Locale = (typeof locales)[number]

const KEY = 'kritzellm.locale'

function isLocale(value: unknown): value is Locale {
  return locales.includes(value as Locale)
}

function storage(): Storage | null {
  try {
    return globalThis.localStorage
  } catch {
    // Private windows and blocked site data can throw on access.
    return null
  }
}

/** The language picked before, else the browser's first one we speak, else English. */
export function pickLocale(): Locale {
  const saved = storage()?.getItem(KEY)
  if (isLocale(saved)) return saved
  for (const tag of globalThis.navigator?.languages ?? []) {
    const language = tag.toLowerCase().split('-')[0]
    if (isLocale(language)) return language
  }
  return 'en'
}

export const i18n = createI18n({
  legacy: false,
  locale: pickLocale(),
  fallbackLocale: 'en',
  messages: { en, de },
})

export function currentLocale(): Locale {
  return i18n.global.locale.value as Locale
}

/** Switches the app's language and remembers it on this device. */
export function setLocale(locale: Locale) {
  i18n.global.locale.value = locale
  document.documentElement.lang = locale
  try {
    storage()?.setItem(KEY, locale)
  } catch {
    // Not remembered, but the switch still holds for this visit.
  }
}

/** The cottage library's words for the current language; English is its own default. */
export function uiMessages() {
  return currentLocale() === 'de' ? uiGerman : undefined
}
