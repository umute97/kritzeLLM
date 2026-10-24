import type { Tone } from './types'

// Ground, border, text and dot per tone. The word always says it; colour only hints.
export const toneClasses: Record<Tone, { chip: string; dot: string }> = {
  plain: { chip: 'bg-paper border-edge text-ink', dot: 'bg-transparent border-ink' },
  lemon: { chip: 'bg-lemon-soft border-lemon text-ink', dot: 'bg-lemon border-ink' },
  orchid: { chip: 'bg-orchid-soft border-orchid text-ink', dot: 'bg-orchid border-ink' },
  herb: { chip: 'bg-herb-soft border-herb text-ink', dot: 'bg-herb border-ink' },
  bark: { chip: 'bg-bark border-bark text-cream', dot: 'bg-cream border-cream' },
}
