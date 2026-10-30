import type { IconName } from './icons'
import type { Tone } from './types'

// Ground, border, text and dot per tone. The word always says it; colour only hints.
export const toneClasses: Record<Tone, { chip: string; dot: string }> = {
  plain: { chip: 'bg-paper border-edge text-ink', dot: 'bg-transparent border-ink' },
  lemon: { chip: 'bg-lemon-soft border-lemon text-ink', dot: 'bg-lemon border-ink' },
  orchid: { chip: 'bg-orchid-soft border-orchid text-ink', dot: 'bg-orchid border-ink' },
  herb: { chip: 'bg-herb-soft border-herb text-ink', dot: 'bg-herb border-ink' },
  bark: { chip: 'bg-bark border-bark text-cream', dot: 'bg-cream border-cream' },
}

export type Intent = 'success' | 'info' | 'warning' | 'error'

// Icon, badge and card per intent of a banner or toast.
export const intentLooks: Record<Intent, { icon: IconName; badge: string; card: string }> = {
  success: { icon: 'check', badge: 'bg-herb text-ink', card: 'bg-paper border-[1.5px] border-ink' },
  info: { icon: 'info', badge: 'bg-orchid text-ink', card: 'bg-paper border-[1.5px] border-ink' },
  warning: {
    icon: 'alert-circle',
    badge: 'bg-lemon text-ink',
    card: 'bg-lemon-soft border-[1.5px] border-ink',
  },
  error: { icon: 'alert', badge: 'bg-bark text-cream', card: 'bg-bark-soft border-2 border-bark' },
}
