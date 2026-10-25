// Shared look of every text-like control: resting, focused, wrong and disabled.
export function fieldClass(state: { invalid?: boolean; disabled?: boolean }) {
  return [
    'w-full rounded-field bg-paper text-base text-ink placeholder:text-hint transition-shadow focus:outline-none focus:ring-4 focus:ring-accent/55',
    state.disabled
      ? 'cursor-not-allowed border-[1.5px] border-dashed border-edge bg-mute text-muted'
      : state.invalid
        ? 'border-2 border-bark bg-bark-soft focus:border-bark'
        : 'border-[1.5px] border-edge focus:border-ink',
  ]
}
