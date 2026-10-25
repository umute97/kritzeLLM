<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import { plural } from '@/utils/format'
import { useUploads } from '@/stores/uploads'
import { KButton, KProgressBar, KUploadRow } from '@/ui'

// The batch card next to the dropzone: one row per photo, following it to "Ready".
defineProps<{ journalName: string }>()

const uploads = useUploads()

const total = computed(() => uploads.rows.length)
const settled = computed(() => total.value - uploads.counts.busy)
const summary = computed(() => {
  const { done, skipped, failed } = uploads.counts
  return [
    `${done} done`,
    skipped && `${skipped} skipped`,
    failed && `${failed} ${failed === 1 ? 'needs' : 'need'} a hand`,
  ]
    .filter(Boolean)
    .join(' · ')
})
</script>

<template>
  <section
    aria-labelledby="batch-title"
    class="flex min-w-0 flex-[1_1_420px] flex-col gap-4 rounded-card border-[1.5px] border-ink bg-cream px-5 py-5.5 sm:px-7"
  >
    <div class="flex flex-wrap items-baseline justify-between gap-2.5">
      <h2 id="batch-title" class="m-0 text-[22px]">
        {{ plural(total, 'photo') }} into {{ journalName }}
      </h2>
      <span class="text-sm text-muted">{{ summary }}</span>
    </div>
    <KProgressBar :value="settled" :max="total" label="Upload progress" />
    <ul class="m-0 flex list-none flex-col gap-2 p-0">
      <KUploadRow
        v-for="row in uploads.rows"
        :key="row.key"
        :file-name="row.fileName"
        :status="row.status"
        :status-label="row.statusLabel"
        :note="row.note"
        :progress="row.progress"
      >
        <RouterLink
          v-if="row.pageId && (row.status === 'ready' || row.status === 'duplicate')"
          :to="{ name: 'page', params: { pageId: row.pageId } }"
          class="text-[13px] font-bold"
          >Open</RouterLink
        >
      </KUploadRow>
    </ul>
    <KButton
      v-if="!uploads.active"
      variant="quiet"
      size="sm"
      class="self-end"
      @click="uploads.clear()"
    >
      Clear the list
    </KButton>
  </section>
</template>
