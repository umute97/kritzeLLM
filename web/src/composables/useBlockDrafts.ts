import { onUnmounted, reactive, type Ref } from 'vue'
import { useI18n } from 'vue-i18n'

import type { Block, PageDetail } from '@/api/types'
import { usePages } from '@/stores/pages'
import { useToasts } from '@/ui'
import { toastError } from '@/utils/notify'

const SAVED_MS = 2500

/**
 * Editing a page's blocks: unsaved drafts over the saved text, the blocks still saving, and a
 * short "saved" after each save. A saved block replaces its old self in `detail`.
 */
export function useBlockDrafts(detail: Ref<PageDetail | undefined>) {
  const { t } = useI18n()
  const pages = usePages()
  const toasts = useToasts()
  const drafts = reactive(new Map<string, string>())
  const saving = reactive(new Set<string>())
  const saved = reactive(new Set<string>())
  const savedTimers = new Map<string, ReturnType<typeof setTimeout>>()

  function text(block: Block): string {
    return drafts.get(block.id) ?? block.text
  }

  function setText(block: Block, value: string) {
    if (value === block.text) drafts.delete(block.id)
    else drafts.set(block.id, value)
  }

  function replace(updated: Block) {
    if (!detail.value) return
    detail.value = {
      ...detail.value,
      blocks: detail.value.blocks.map((b) => (b.id === updated.id ? updated : b)),
    }
  }

  function flashSaved(id: string) {
    saved.add(id)
    clearTimeout(savedTimers.get(id))
    savedTimers.set(
      id,
      setTimeout(() => saved.delete(id), SAVED_MS),
    )
  }

  async function patch(block: Block, changes: { text?: string; uncertain?: boolean }) {
    if (saving.has(block.id)) return
    saving.add(block.id)
    try {
      const updated = await pages.patchBlock(block.id, changes)
      replace(updated)
      // Whatever was typed while it saved stays a draft on top of the saved text.
      if (drafts.get(block.id) === updated.text) drafts.delete(block.id)
      flashSaved(block.id)
    } catch (error) {
      toastError(error, t('page.saveFailed', { n: block.seq + 1 }), {
        retry: () => void patch(block, changes),
        byStatus: { 409: { tone: 'warning', detail: t('page.busy') } },
      })
    } finally {
      saving.delete(block.id)
    }
  }

  function save(block: Block) {
    const draft = drafts.get(block.id)
    if (draft === undefined) return
    if (!draft.trim()) {
      toasts.push({ tone: 'info', title: t('page.blockEmptyTitle'), detail: t('page.blockEmpty') })
      return
    }
    return patch(block, { text: draft })
  }

  const looksRight = (block: Block) => patch(block, { uncertain: false })

  onUnmounted(() => savedTimers.forEach(clearTimeout))

  return { drafts, saving, saved, text, setText, save, looksRight }
}
