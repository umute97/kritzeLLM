import { inject, type App, type Component, type InjectionKey } from 'vue'

export interface CottageOptions {
  /** What a component given `to` renders, e.g. `RouterLink`. Without one it's a plain `<a href>`. */
  link?: Component
}

const linkKey: InjectionKey<string | Component> = Symbol('cottage link')

/** App-wide settings for the library: `app.use(createCottage({ link: RouterLink }))`. */
export function createCottage(options: CottageOptions = {}) {
  return {
    install(app: App) {
      if (options.link) app.provide(linkKey, options.link)
    },
  }
}

export function useLinkComponent(): string | Component {
  return inject(linkKey, 'a')
}
