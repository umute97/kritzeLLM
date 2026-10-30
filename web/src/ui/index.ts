// The cottage component library. Every screen is built from these pieces; the design notes live
// in docs/design/README.md.

export { createCottage, type CottageOptions } from './plugin'
export type { LinkTarget } from './polymorphic'

// Brand and icons
export { default as KDoodle } from './KDoodle.vue'
export { default as KIcon } from './KIcon.vue'
export { default as KLogo } from './KLogo.vue'
export { icons, type IconName } from './icons'

// Buttons and fields
export { default as KButton } from './KButton.vue'
export { default as KCheckbox } from './KCheckbox.vue'
export { default as KFieldNote } from './KFieldNote.vue'
export { default as KFieldShell } from './KFieldShell.vue'
export { default as KIconButton } from './KIconButton.vue'
export { default as KSearchField } from './KSearchField.vue'
export { default as KSelect } from './KSelect.vue'
export { default as KSwitch } from './KSwitch.vue'
export { default as KTextArea } from './KTextArea.vue'
export { default as KTextField } from './KTextField.vue'

// Chips, tags and pickers
export { default as KBadge } from './KBadge.vue'
export { default as KBlockKindTag } from './KBlockKindTag.vue'
export { default as KChip } from './KChip.vue'
export { default as KFilterChips } from './KFilterChips.vue'
export { default as KFlag } from './KFlag.vue'
export { default as KSegmented } from './KSegmented.vue'
export { default as KStatusChip } from './KStatusChip.vue'

// Feedback and overlays
export { default as KBanner } from './KBanner.vue'
export { default as KDialog } from './KDialog.vue'
export { default as KIconBadge } from './KIconBadge.vue'
export { default as KMenu } from './KMenu.vue'
export { default as KToast } from './KToast.vue'
export { default as KToastStack } from './KToastStack.vue'
export { default as KTooltip } from './KTooltip.vue'
export { AUTO_DISMISS_MS, useToasts, type Toast, type ToastOptions, type ToastTone } from './toasts'

// Navigation
export { default as KBreadcrumb } from './KBreadcrumb.vue'
export { default as KLoadMore } from './KLoadMore.vue'
export { default as KNavLink } from './KNavLink.vue'
export { default as KPager } from './KPager.vue'
export { default as KTopNav } from './KTopNav.vue'

// Progress and empty states
export { default as KEmptyState } from './KEmptyState.vue'
export { default as KProgressBar } from './KProgressBar.vue'
export { default as KSkeleton } from './KSkeleton.vue'
export { default as KSpinner } from './KSpinner.vue'
export { default as KTypingDots } from './KTypingDots.vue'

// Journals, pages and uploads
export { default as KAddTile } from './KAddTile.vue'
export { default as KBlockCard } from './KBlockCard.vue'
export { default as KDropzone } from './KDropzone.vue'
export { default as KJournalCover } from './KJournalCover.vue'
export { default as KPageCard } from './KPageCard.vue'
export { default as KUploadRow } from './KUploadRow.vue'

// Search and chat
export { default as KCitationChip } from './KCitationChip.vue'
export { default as KComposer } from './KComposer.vue'
export { default as KHighlight } from './KHighlight.vue'
export { default as KMessage } from './KMessage.vue'
export { default as KScoreBars } from './KScoreBars.vue'
export { default as KSearchResult } from './KSearchResult.vue'
export { default as KSourceCard } from './KSourceCard.vue'
export { default as KToolActivity } from './KToolActivity.vue'

export * from './types'
