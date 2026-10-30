<script setup lang="ts">
import { computed, ref, useId, watch } from 'vue'

import { plural } from '@/utils/format'
import { useUploads } from '@/stores/uploads'
import { KButton, KProgressBar, KSection, KUploadRow } from '@/ui'

// The batch strip above the journal's pages: overall progress, with one row per photo behind a
// toggle, following it to "Ready".
const props = defineProps<{ journalId: string; journalName: string }>()

const uploads = useUploads()
const listId = useId()

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

const open = ref(false)
// Trouble opens the list, so a skipped or failed photo is never tucked away.
watch(
  () => batch.value.counts.skipped + batch.value.counts.failed,
  (trouble, before = 0) => {
    if (trouble > before) open.value = true
  },
  { immediate: true },
)
</script>

<template>
  <KSection
    :title="`${plural(total, 'photo')} into ${journalName}`"
    :heading-level="3"
    framed
    align="baseline"
  >
    <template #aside>
      <span class="text-sm text-muted">{{ summary }}</span>
      <KButton
        variant="quiet"
        size="sm"
        :aria-expanded="open"
        :aria-controls="listId"
        @click="open = !open"
      >
        {{ open ? 'Hide each photo' : 'Show each photo' }}
      </KButton>
    </template>
    <KProgressBar :value="settled" :max="total" label="Upload progress" />
    <ul v-show="open" :id="listId" class="m-0 flex list-none flex-col gap-2 p-0">
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
