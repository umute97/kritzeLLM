import { computed, toValue, type Component, type MaybeRefOrGetter } from 'vue'

type ButtonType = 'button' | 'submit' | 'reset'

function stay(event: Event) {
  event.preventDefault()
  event.stopImmediatePropagation()
}

/**
 * Attributes for something that is a `<button>` unless `as` makes it a link. A link has no
 * native `disabled`, so an inactive one says `aria-disabled`, leaves the tab order and swallows
 * the click before the router sees it.
 */
export function usePolymorphic(
  as: MaybeRefOrGetter<string | Component>,
  inactive: MaybeRefOrGetter<boolean | undefined>,
  type: MaybeRefOrGetter<ButtonType> = 'button',
) {
  return computed(() => {
    const off = !!toValue(inactive)
    if (toValue(as) === 'button') return { type: toValue(type), disabled: off }
    return off ? { 'aria-disabled': 'true' as const, tabindex: -1, onClickCapture: stay } : {}
  })
}
