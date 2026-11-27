<script setup lang="ts">
import { computed, nextTick, useTemplateRef, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import type { Source } from '@/api/types'
import { useJournals } from '@/stores/journals'
import { KSection, KSourceCard } from '@/ui'
import { formatEntryDates } from '@/utils/format'

// The pages an answer cites, one card per citation. The picked ones lift and come into view.
const props = defineProps<{ sources: Source[]; picked?: number[] }>()

const { t } = useI18n()
const journals = useJournals()
const list = useTemplateRef('list')

// The journal only matters once there's more than one.
const severalJournals = computed(() => journals.byId.size > 1)

function title(source: Source): string {
  const page = t('chat.sourcePage', { n: source.pageNumber })
  const journal = journals.byId.get(source.journalId)?.name
  return severalJournals.value && journal ? `${page} · ${journal}` : page
}

watch(
  () => props.picked,
  async (refs) => {
    await nextTick()
    list.value
      ?.querySelector(`[data-ref="${refs?.[0]}"]`)
      ?.scrollIntoView?.({ block: 'nearest', behavior: 'smooth' })
  },
)
</script>

<template>
  <KSection :title="t('chat.sources')">
    <ul v-if="sources.length" ref="list" class="flex flex-col gap-3">
      <li v-for="source in sources" :key="source.ref" :data-ref="source.ref">
        <KSourceCard
          :title="title(source)"
          :date="formatEntryDates(source.entryDates)"
          :quote="source.quote"
          :selected="picked?.includes(source.ref)"
          :to="{
            name: 'page',
            params: { pageId: source.pageId },
            query: { blocks: source.blockId },
          }"
        />
      </li>
    </ul>
    <p v-else class="m-0 font-hand text-[19px] text-bark">{{ t('chat.noSources') }}</p>
  </KSection>
</template>
