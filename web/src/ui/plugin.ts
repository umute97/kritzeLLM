import {
  computed,
  inject,
  toValue,
  type App,
  type Component,
  type InjectionKey,
  type MaybeRefOrGetter,
} from 'vue'

import { englishMessages, mergeMessages, messagesKey, type UiMessagesOverride } from './messages'

export interface CottageOptions {
  /** What a component given `to` renders, e.g. `RouterLink`. Without one it's a plain `<a href>`. */
  link?: Component
  /** Words to say instead of the English ones; a ref or getter keeps them live, e.g. for i18n. */
  messages?: MaybeRefOrGetter<UiMessagesOverride | undefined>
}

const linkKey: InjectionKey<string | Component> = Symbol('cottage link')

/** App-wide settings for the library: `app.use(createCottage({ link: RouterLink }))`. */
export function createCottage(options: CottageOptions = {}) {
  return {
    install(app: App) {
      if (options.link) app.provide(linkKey, options.link)
      if (options.messages)
        app.provide(
          messagesKey,
          computed(() => mergeMessages(englishMessages, toValue(options.messages))),
        )
    },
  }
}

export function useLinkComponent(): string | Component {
  return inject(linkKey, 'a')
}
