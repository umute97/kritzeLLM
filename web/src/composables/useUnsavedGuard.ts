import { onUnmounted } from 'vue'
import { onBeforeRouteLeave, onBeforeRouteUpdate, type RouteLocationNormalized } from 'vue-router'

/**
 * While `unsaved()`, holds any route change and hands where it was going to `ask`, and makes the
 * browser ask before the tab closes or reloads.
 */
export function useUnsavedGuard(
  unsaved: () => boolean,
  ask: (to: RouteLocationNormalized) => void,
) {
  function hold(to: RouteLocationNormalized) {
    if (!unsaved()) return true
    ask(to)
    return false
  }

  onBeforeRouteLeave(hold)
  onBeforeRouteUpdate(hold)

  function holdUnload(event: BeforeUnloadEvent) {
    if (unsaved()) event.preventDefault()
  }

  window.addEventListener('beforeunload', holdUnload)
  onUnmounted(() => window.removeEventListener('beforeunload', holdUnload))
}
