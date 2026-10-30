import { computed, type Component } from 'vue'

import { useLinkComponent } from './plugin'

type ButtonType = 'button' | 'submit' | 'reset'

export type LinkTarget = string | Record<string, unknown>

/** `to` for a link component, `href` for a plain `<a>` (which can only follow a path). */
export function linkAttrs(is: string | Component, to: LinkTarget) {
  return typeof is === 'string' ? { href: typeof to === 'string' ? to : undefined } : { to }
}

function stay(event: Event) {
  event.preventDefault()
  event.stopImmediatePropagation()
}

/**
 * What to render and with which attributes, for something that can be a button or a link.
 * `as` wins; otherwise `to` makes it the app's link component (see `createCottage`), and
 * without either it's `fallback`. A link has no native `disabled`, so an inactive one says
 * `aria-disabled`, leaves the tab order and swallows the click before the router sees it.
 */
export function usePolymorphic(
  source: () => {
    as?: string | Component
    to?: LinkTarget
    inactive?: boolean
    type?: ButtonType
  },
  fallback: string | Component = 'button',
) {
  const link = useLinkComponent()
  return computed(() => {
    const { as, to, inactive, type = 'button' } = source()
    const is = as ?? (to !== undefined ? link : fallback)
    const attrs: Record<string, unknown> = to !== undefined ? linkAttrs(is, to) : {}
    if (is === 'button') Object.assign(attrs, { type, disabled: !!inactive })
    else if (inactive)
      Object.assign(attrs, { 'aria-disabled': 'true', tabindex: -1, onClickCapture: stay })
    return { is, attrs }
  })
}
