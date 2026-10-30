// Class strings that several components share, so the same state looks the same everywhere.

export const focusRing = 'focus:outline-none focus:ring-4 focus:ring-accent/55'
export const focusWithinRing = 'focus-within:ring-4 focus-within:ring-accent/55'

export const disabledClass =
  'cursor-not-allowed border-[1.5px] border-dashed border-edge bg-mute text-muted'

export const coverShape = 'h-[132px] w-full rounded-[9px_18px_18px_9px]'

// Shared look of every text-like control: resting, focused, wrong and disabled.
export function fieldClass(state: { invalid?: boolean; disabled?: boolean }) {
  return [
    'w-full rounded-field bg-paper text-base text-ink placeholder:text-hint transition-shadow',
    focusRing,
    state.disabled
      ? disabledClass
      : state.invalid
        ? 'border-2 border-bark bg-bark-soft focus:border-bark'
        : 'border-[1.5px] border-edge focus:border-ink',
  ]
}

// A `framed` pill keeps its line when it's not picked; an unframed one sits on a track that draws it.
export function pillClass(state: { on: boolean; framed?: boolean; disabled?: boolean }) {
  return [
    'inline-flex items-center gap-1.5 rounded-full border-[1.5px] font-bold text-ink',
    state.disabled ? 'cursor-not-allowed opacity-60' : 'cursor-pointer',
    state.on
      ? 'border-ink bg-accent'
      : [
          state.framed ? 'border-ink bg-paper' : 'border-transparent',
          !state.disabled && 'hover:bg-cream',
        ],
  ]
}
