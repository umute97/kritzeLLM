<script setup lang="ts">
import { computed, ref, useId, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import type { Batch, ShownRow } from '@/stores/uploads'
import { KButton, KDisclosure, KProgressBar, KSection, KUploadRow } from '@/ui'
import { fileSize } from '@/utils/format'
import { MAX_BYTES } from '@/utils/photos'

// The batch strip above the journal's pages: overall progress, with one row per photo behind a
// toggle, following it to "Ready".
const props = defineProps<{ batch: Batch; journalName: string }>()
const emit = defineEmits<{ clear: [] }>()

const { t } = useI18n()
const listId = useId()

const total = computed(() => props.batch.rows.length)
const settled = computed(() => total.value - props.batch.counts.busy)
const summary = computed(() => {
  const { done, skipped, failed, deleted } = props.batch.counts
  return [
    t('uploads.done', { n: done }),
    skipped && t('uploads.skipped', { n: skipped }),
    failed && t('uploads.failed', failed),
    deleted && t('uploads.deleted', { n: deleted }),
  ]
    .filter(Boolean)
    .join(' · ')
})

function words(row: ShownRow): { note?: string; statusLabel?: string; progress?: number } {
  const n = row.pageNumber
  switch (row.status) {
    case 'sending': {
      const sent = row.sent ?? 0
      const total = row.total ?? 0
      return {
        progress: total ? Math.round((sent / total) * 100) : 0,
        note: t('uploads.sent', { sent: fileSize(sent), total: fileSize(total) }),
      }
    }
    case 'failed':
      if (row.reason === 'type') {
        return { statusLabel: t('uploads.notPhoto'), note: t('uploads.notPhotoNote') }
      }
      if (row.reason === 'size') {
        const size = fileSize(row.total ?? 0)
        return {
          statusLabel: t('uploads.tooBig'),
          note: t('uploads.tooBigNote', { size, limit: fileSize(MAX_BYTES) }),
        }
      }
      if (row.reason === 'stopped') return { note: t('uploads.notUpRetry') }
      return {
        statusLabel: row.problem?.status === 413 ? t('uploads.tooBig') : undefined,
        note:
          row.problem?.detail ??
          row.problem?.title ??
          (n === undefined ? t('uploads.notUp') : t('common.page', { n })),
      }
    case 'deleted':
      return { note: t('uploads.pageDeleted') }
    case 'duplicate':
      return { note: t('uploads.samePhoto', { n }) }
    case 'queued':
      return { note: t('uploads.waiting', { n }) }
    case 'transcribing':
      return { note: t('uploads.reading', { n }) }
    case 'indexing':
      return { note: t('uploads.indexing', { n }) }
    case 'ready':
      return { note: t('common.page', { n }) }
  }
}

const rows = computed(() => props.batch.rows.map((row) => ({ ...row, ...words(row) })))

const open = ref(false)
// Trouble opens the list, so a skipped or failed photo is never tucked away.
watch(
  () => props.batch.counts.skipped + props.batch.counts.failed,
  (trouble, before = 0) => {
    if (trouble > before) open.value = true
  },
  { immediate: true },
)
</script>

<template>
  <KSection
    :title="t('uploads.title', { photos: t('counts.photos', total), journal: journalName })"
    :heading-level="3"
    framed
    align="baseline"
  >
    <template #aside>
      <span class="text-sm text-muted">{{ summary }}</span>
      <KDisclosure v-model:open="open" :controls="listId" variant="quiet">
        {{ open ? t('uploads.hideEach') : t('uploads.showEach') }}
      </KDisclosure>
    </template>
    <KProgressBar :value="settled" :max="total" :label="t('uploads.progress')" />
    <ul v-show="open" :id="listId" class="m-0 flex list-none flex-col gap-2 p-0">
      <KUploadRow
        v-for="row in rows"
        :key="row.key"
        :file-name="row.fileName"
        :status="row.status"
        :status-label="row.statusLabel"
        :note="row.note"
        :progress="row.progress"
      >
        <KButton
          v-if="row.pageId && (row.status === 'ready' || row.status === 'duplicate')"
          :to="{ name: 'page', params: { pageId: row.pageId } }"
          variant="quiet"
          size="sm"
        >
          {{ t('uploads.open') }}
        </KButton>
      </KUploadRow>
    </ul>
    <KButton v-if="!batch.active" variant="quiet" size="sm" class="self-end" @click="emit('clear')">
      {{ t('uploads.clear') }}
    </KButton>
  </KSection>
</template>
