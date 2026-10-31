import { config } from '@vue/test-utils'

import { i18n } from '@/i18n'

// Tests read English, and a key missing from the catalogs fails loudly instead of showing as itself.
i18n.global.locale.value = 'en'
i18n.global.setMissingHandler((locale, key) => {
  throw new Error(`No ${locale} message for ${key}`)
})
config.global.plugins.push(i18n)

// jsdom has <dialog> but not its modal methods yet; this is just enough of them for the tests.
if (!HTMLDialogElement.prototype.showModal) {
  HTMLDialogElement.prototype.showModal = function () {
    this.open = true
  }
  HTMLDialogElement.prototype.close = function () {
    if (!this.open) return
    this.open = false
    this.dispatchEvent(new Event('close'))
  }
}
