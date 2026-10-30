<script setup lang="ts">
import { computed } from 'vue'

import { useAuthedImage } from '@/api/images'
import type { Page } from '@/api/types'
import { formatEntryDates } from '@/utils/format'
import { KPageCard } from '@/ui'

// A page card with its real thumbnail, linking to Page detail.
const props = defineProps<{ page: Page; tilt?: number }>()
const emit = defineEmits<{ retry: [page: Page] }>()

const thumbnail = useAuthedImage(() => props.page.image.urls.thumbnail)
const date = computed(() => formatEntryDates(props.page.entryDates))
</script>

<template>
  <KPageCard
    :to="{ name: 'page', params: { pageId: page.id } }"
    :page-number="page.pageNumber"
    :status="page.status"
    :date="date"
    :image-url="thumbnail"
    :tilt="tilt"
    :failed-text="page.error?.title ?? 'couldn’t read this one'"
    @retry="emit('retry', page)"
  />
</template>
