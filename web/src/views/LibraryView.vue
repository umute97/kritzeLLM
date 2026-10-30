<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { ApiError } from '@/api/errors'
import type { Journal, Page } from '@/api/types'
import JournalDialog from '@/components/JournalDialog.vue'
import PageThumb from '@/components/PageThumb.vue'
import UploadBatch from '@/components/UploadBatch.vue'
import { useAction } from '@/composables/useAction'
import { useConfirm } from '@/composables/useConfirm'
import { coverColor } from '@/utils/covers'
import { plural } from '@/utils/format'
import { toastError } from '@/utils/notify'
import { PER_SHELF, useJournals } from '@/stores/journals'
import { usePages } from '@/stores/pages'
import { useUploads } from '@/stores/uploads'
import {
  KAddTile,
  KButton,
  KCardGrid,
  KConfirmDialog,
  KDoodle,
  KDropzone,
  KEmptyState,
  KFilterChips,
  KJournalCover,
  KLoadMore,
  KMenu,
  KPage,
  KPageHeader,
  KPager,
  KSection,
  tiltFor,
  useToasts,
  type MenuItem,
} from '@/ui'

const props = defineProps<{ journalId?: string }>()

const router = useRouter()
const journals = useJournals()
const pages = usePages()
const uploads = useUploads()
const toasts = useToasts()

type Filter = 'all' | 'ready' | 'failed'
const filters: { value: Filter; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'ready', label: 'Ready' },
  { value: 'failed', label: 'Needs a hand' },
]
const filter = ref<Filter>('all')
const dropError = ref<string>()
const newJournal = ref(false)
const renaming = ref(false)
const deleting = useConfirm<Journal>()

const journal = computed(() => (props.journalId ? journals.byId.get(props.journalId) : undefined))
const batch = computed(() => (journal.value ? uploads.batch(journal.value.id) : undefined))
const roomOnShelf = computed(
  () => journals.loaded && !journals.canNext && journals.shelf.length < PER_SHELF,
)

async function openShelf() {
  try {
    if (!journals.loaded) await journals.show(0)
    if (!props.journalId && journals.shelf[0]) {
      await router.replace({ name: 'journal', params: { journalId: journals.shelf[0].id } })
    }
  } catch (error) {
    toastError(error, 'Couldn’t open the shelf', { retry: openShelf })
  }
}

async function loadPages() {
  if (!props.journalId) return
  try {
    await journals.get(props.journalId)
    await pages.load(props.journalId, filter.value === 'all' ? undefined : filter.value)
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      toasts.push({ tone: 'info', title: 'That journal is gone', detail: 'Back to the shelf.' })
      await router.replace({ name: 'library' })
      return
    }
    toastError(error, 'Couldn’t load the pages', { retry: loadPages })
  }
}

onMounted(openShelf)
watch([() => props.journalId, filter], loadPages, { immediate: true })
watch(
  () => props.journalId,
  () => {
    dropError.value = undefined
  },
)

const shelfStep = useAction((step: 'back' | 'next') => journals[step](), {
  title: 'Couldn’t turn the shelf',
})
const retry = useAction((page: Page) => pages.retranscribe(page), {
  title: (page) => `Couldn’t read page ${page.pageNumber} again`,
})
const more = useAction(() => pages.more(), { title: 'Couldn’t load more pages' })

function onFiles(files: File[]) {
  if (!journal.value) return
  dropError.value = uploads.add(journal.value.id, files) ?? undefined
}

function onCreated(created: Journal) {
  toasts.push({
    tone: 'success',
    title: 'A new journal',
    detail: `${created.name} is on the shelf.`,
  })
  void router.push({ name: 'journal', params: { journalId: created.id } })
}

const menu = computed<MenuItem[]>(() => [
  { id: 'rename', label: 'Rename journal', icon: 'pencil', run: () => (renaming.value = true) },
  {
    id: 'delete',
    label: 'Delete journal',
    icon: 'trash',
    danger: true,
    // Photos still going up would land in a journal that's gone.
    disabled: batch.value?.active,
    hint: 'Photos are still going up',
    run: () => journal.value && deleting.ask(journal.value),
  },
])

const deleteNote = computed(() => {
  const count = deleting.subject?.pageCount ?? 0
  const what = count
    ? `Its ${plural(count, 'page')} and all their text go with it.`
    : 'It has no pages yet.'
  return `${what} This can’t be undone.`
})

function deleteJournal() {
  return deleting.run(
    async (gone) => {
      await journals.remove(gone.id)
      uploads.forget(gone.id)
      pages.forgetJournal(gone.id)
      toasts.push({ tone: 'info', title: `${gone.name} is gone` })
      const first = journals.shelf[0]
      await router.replace(
        first ? { name: 'journal', params: { journalId: first.id } } : { name: 'library' },
      )
    },
    { title: 'Couldn’t delete the journal' },
  )
}

const summary = computed(() => {
  const shown = pages.items.length
  if (filter.value === 'all' && journal.value) {
    return `Showing ${shown} of ${plural(journal.value.pageCount, 'page')}`
  }
  return `Showing ${plural(shown, filter.value === 'ready' ? 'ready page' : 'page that needs a hand', filter.value === 'ready' ? 'ready pages' : 'pages that need a hand')}`
})
</script>

<template>
  <KPage gap="lg">
    <KPageHeader title="Your journals" subtitle="pick a notebook, or tuck in some new pages">
      <template #actions>
        <KButton variant="second" icon="plus" @click="newJournal = true">New journal</KButton>
      </template>
    </KPageHeader>

    <KEmptyState
      v-if="journals.empty"
      title="Your shelf is empty"
      text="Start a journal, then add photos of its pages."
      doodle="daisy"
    >
      <KButton @click="newJournal = true">New journal</KButton>
    </KEmptyState>

    <template v-else>
      <KSection title="On the shelf">
        <template #aside>
          <KPager
            v-if="journals.loaded"
            text-first
            prev-label="Previous journals"
            next-label="More journals"
            :can-prev="journals.canBack && !journals.loading"
            :can-next="journals.canNext && !journals.loading"
            @prev="shelfStep.run('back')"
            @next="shelfStep.run('next')"
          >
            <span class="text-sm text-muted">{{ journals.range }}</span>
          </KPager>
        </template>
        <KCardGrid kind="covers" :loading="!journals.loaded">
          <li v-for="item in journals.shelf" :key="item.id">
            <KJournalCover
              :to="{ name: 'journal', params: { journalId: item.id } }"
              :name="item.name"
              :meta="plural(item.pageCount, 'page')"
              :color="coverColor(item.id)"
              :selected="item.id === journalId"
            />
          </li>
          <li v-if="roomOnShelf">
            <KAddTile label="New journal" @click="newJournal = true" />
          </li>
        </KCardGrid>
      </KSection>

      <section v-if="journal" aria-label="Upload pages" class="flex flex-wrap gap-6">
        <KDropzone
          class="min-w-0 flex-[1_1_420px]"
          title="Drop page photos here"
          choose-label="Choose photos"
          :count-label="(n) => plural(n, 'photo')"
          :hint="`JPEG, PNG, HEIC or WebP, up to 25 MB each. They go into ${journal.name}.`"
          :error="dropError"
          error-hint="Photos only: JPEG, PNG, HEIC or WebP, up to 25 MB each. PDF import is coming."
          @files="onFiles"
        >
          <template #illustration><KDoodle name="daisy" :size="52" /></template>
        </KDropzone>
        <UploadBatch
          v-if="batch?.rows.length"
          :journal-id="journal.id"
          :journal-name="journal.name"
        />
      </section>

      <KSection
        v-if="journal"
        :title="journal.name"
        :description="journal.description ?? undefined"
        size="lg"
        align="end"
      >
        <template #title-after>
          <KMenu label="Journal actions" :items="menu" align="start" />
        </template>
        <template #aside>
          <KFilterChips v-model="filter" label="Filter pages" :options="filters" />
        </template>

        <KCardGrid
          v-if="pages.items.length || pages.loading"
          kind="pages"
          :loading="!pages.items.length"
        >
          <li v-for="(page, index) in pages.items" :key="page.id">
            <PageThumb :page="page" :tilt="tiltFor(index)" @retry="retry.run" />
          </li>
        </KCardGrid>
        <KEmptyState
          v-else-if="filter !== 'all'"
          title="All cosy and calm"
          :text="
            filter === 'failed' ? 'No pages need a hand right now.' : 'No pages are ready yet.'
          "
        >
          <KButton variant="second" @click="filter = 'all'">Show all pages</KButton>
        </KEmptyState>
        <KEmptyState
          v-else
          title="No pages yet"
          :text="`${journal.name} is waiting for its first photo. Drop some above.`"
        />

        <KLoadMore
          v-if="pages.items.length"
          :summary="summary"
          :has-more="pages.nextCursor !== null"
          :loading="pages.loading"
          label="Show more pages"
          @more="more.run()"
        />
      </KSection>
    </template>

    <JournalDialog v-model:open="newJournal" @created="onCreated" />
    <JournalDialog v-model:open="renaming" :journal="journal" />

    <KConfirmDialog
      v-model:open="deleting.open"
      :title="`Delete ${deleting.subject?.name}?`"
      :description="deleteNote"
      confirm-label="Delete journal"
      :loading="deleting.busy"
      @confirm="deleteJournal"
    />
  </KPage>
</template>
