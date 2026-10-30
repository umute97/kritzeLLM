<script setup lang="ts">
import { computed } from 'vue'

import { plural } from '@/utils/format'
import { useUploads } from '@/stores/uploads'
import { KButton, KProgressBar, KSection, KUploadRow } from '@/ui'

// The batch card next to the dropzone: one row per photo into this journal, following it to
// "Ready".
const props = defineProps<{ journalId: string; journalName: string }>()

const uploads = useUploads()

const batch = computed(() => uploads.batch(props.journalId))
const total = computed(() => batch.value.rows.length)
const settled = computed(() => total.value - batch.value.counts.busy)
const summary = computed(() => {
  const { done, skipped, failed, deleted } = batch.value.counts
  return [
    `${done} done`,
    skipped && `${skipped} skipped`,
    failed && `${failed} ${failed === 1 ? 'needs' : 'need'} a hand`,
    deleted && `${deleted} deleted`,
  ]
    .filter(Boolean)
    .join(' · ')
})
</script>

<template>
  <KSection
    :title="`${plural(total, 'photo')} into ${journalName}`"
    framed
    align="baseline"
    class="flex-[1_1_420px]"
  >
    <template #aside>
      <span class="text-sm text-muted">{{ summary }}</span>
    </template>
    <KProgressBar :value="settled" :max="total" label="Upload progress" />
    <ul class="m-0 flex list-none flex-col gap-2 p-0">
      <KUploadRow
        v-for="row in batch.rows"
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
          Open
        </KButton>
      </KUploadRow>
    </ul>
    <KButton
      v-if="!batch.active"
      variant="quiet"
      size="sm"
      class="self-end"
      @click="uploads.clear(journalId)"
    >
      Clear the list
    </KButton>
  </KSection>
</template>
