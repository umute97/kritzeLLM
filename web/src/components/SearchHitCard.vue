<script setup lang="ts">
import { computed } from 'vue'

import { useAuthedImage } from '@/api/images'
import type { SearchHit } from '@/api/types'
import { formatEntryDates } from '@/utils/format'
import { pickQuotes } from '@/utils/search'
import { KSearchResult } from '@/ui'

// A search hit with its page's real thumbnail, linking to the page with the matched blocks
// highlighted.
const props = defineProps<{ hit: SearchHit; journal: string; pattern?: RegExp }>()

const thumbnail = useAuthedImage(() => props.hit.page.image.urls.thumbnail)
const date = computed(() => formatEntryDates(props.hit.page.entryDates))
const picked = computed(() => pickQuotes(props.hit.blocks, props.pattern))
const to = computed(() => ({
  name: 'page',
  params: { pageId: props.hit.page.id },
  query: { blocks: props.hit.blocks.map((block) => block.id).join(',') },
}))
</script>

<template>
  <KSearchResult
    :page-number="hit.page.pageNumber"
    :journal="journal"
    :date="date"
    :quotes="picked.quotes"
    :more="picked.more"
    :image-url="thumbnail"
    :to="to"
  />
</template>
