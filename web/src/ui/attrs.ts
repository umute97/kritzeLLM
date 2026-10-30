import { useAttrs } from 'vue'

/** A space-separated id list for `aria-describedby` and friends, or nothing when it's empty. */
export function joinIds(...ids: unknown[]) {
  return ids.filter((id) => typeof id === 'string' && id).join(' ') || undefined
}

/**
 * For a component whose root isn't the real control (use with `inheritAttrs: false`): `class` and
 * `style` lay out the root, everything else (`name`, `id`, `aria-*`, listeners) goes to the control.
 * Functions, not computeds, because `useAttrs()` isn't reactive; call them in the template.
 */
export function useSplitAttrs() {
  const attrs = useAttrs()
  return {
    rootAttrs: () => ({ class: attrs.class, style: attrs.style }),
    controlAttrs: () =>
      Object.fromEntries(
        Object.entries(attrs).filter(([key]) => key !== 'class' && key !== 'style'),
      ),
  }
}

export function noteId(id: string, note: { help?: string; error?: string }) {
  return note.error ? `${id}-error` : note.help ? `${id}-help` : undefined
}
