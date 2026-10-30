<script setup lang="ts">
import { computed, onMounted, ref, useId, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import { api, call } from '@/api/client'
import { ApiError } from '@/api/errors'
import type { Journal, Page } from '@/api/types'
import JournalDialog from '@/components/JournalDialog.vue'
import PageThumb from '@/components/PageThumb.vue'
import UploadBatch from '@/components/UploadBatch.vue'
import { coverColor } from '@/utils/covers'
import { plural } from '@/utils/format'
import { toastError } from '@/utils/notify'
import { useJournals } from '@/stores/journals'
import { usePages } from '@/stores/pages'
import { useUploads } from '@/stores/uploads'
import {
  KButton,
  KDialog,
  KDoodle,
  KDropzone,
  KEmptyState,
  KFilterChips,
  KIcon,
  KJournalCover,
  KLoadMore,
  KMenu,
  KShelfPager,
  KSkeleton,
  tiltFor,
  useToasts,
  type MenuItem,
} from '@/ui'

const props = defineProps<{ journalId?: string }>()

const router = useRouter()
const journals = useJournals()
const pages = usePages()
const uploads = useUploads()

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
const confirmDelete = ref(false)
// The journal the delete dialog asks about, kept while it closes after the journal is gone.
const doomed = ref<Journal>()
const deleting = ref(false)
const shelfTitleId = useId()
const pagesTitleId = useId()

const journal = computed(() => (props.journalId ? journals.byId.get(props.journalId) : undefined))
const batch = computed(() => (journal.value ? uploads.batch(journal.value.id) : undefined))

async function openShelf() {
  try {
    if (!journals.loaded) await journals.show(0)
    if (!props.journalId && journals.shelf[0]) {
      await router.replace({ name: 'journal', params: { journalId: journals.shelf[0].id } })
    }
  } catch (error) {
    toastError(error, 'Couldn’t open the shelf', openShelf)
  }
}

async function loadPages() {
  if (!props.journalId) return
  try {
    await journals.get(props.journalId)
    await pages.load(props.journalId, filter.value === 'all' ? undefined : filter.value)
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      useToasts().push({
        tone: 'info',
        title: 'That journal is gone',
        detail: 'Back to the shelf.',
      })
      await router.replace({ name: 'library' })
      return
    }
    toastError(error, 'Couldn’t load the pages', loadPages)
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

async function shelfStep(step: 'back' | 'next') {
  try {
    await journals[step]()
  } catch (error) {
    toastError(error, 'Couldn’t turn the shelf')
  }
}

function onFiles(files: File[]) {
  if (!journal.value) return
  dropError.value = uploads.add(journal.value.id, files) ?? undefined
}

async function retry(page: Page) {
  try {
    await call(api.POST('/pages/{pageId}/transcribe', { params: { path: { pageId: page.id } } }))
    pages.put({ ...page, status: 'uploaded', error: null })
  } catch (error) {
    toastError(error, `Couldn’t read page ${page.pageNumber} again`)
  }
}

function onCreated(created: Journal) {
  useToasts().push({
    tone: 'success',
    title: 'A new journal',
    detail: `${created.name} is on the shelf.`,
  })
  void router.push({ name: 'journal', params: { journalId: created.id } })
}

const menu = computed<MenuItem[]>(() => [
  { id: 'rename', label: 'Rename journal', icon: 'pencil' },
  // Photos still going up would land in a journal that's gone.
  {
    id: 'delete',
    label: 'Delete journal',
    icon: 'trash',
    danger: true,
    disabled: batch.value?.active,
  },
])

function onMenu(id: string) {
  if (id === 'rename') renaming.value = true
  else if (id === 'delete') {
    doomed.value = journal.value
    confirmDelete.value = true
  }
}

const deleteNote = computed(() => {
  const count = doomed.value?.pageCount ?? 0
  const what = count
    ? `Its ${plural(count, 'page')} and all their text go with it.`
    : 'It has no pages yet.'
  return `${what} This can’t be undone.`
})

async function deleteJournal() {
  const gone = doomed.value
  if (!gone) return
  deleting.value = true
  try {
    await journals.remove(gone.id)
    uploads.forget(gone.id)
    pages.forgetJournal(gone.id)
    confirmDelete.value = false
    useToasts().push({ tone: 'info', title: `${gone.name} is gone` })
    const first = journals.shelf[0]
    await router.replace(
      first ? { name: 'journal', params: { journalId: first.id } } : { name: 'library' },
    )
  } catch (error) {
    toastError(error, 'Couldn’t delete the journal')
  } finally {
    deleting.value = false
  }
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
  <main class="mx-auto flex max-w-[1200px] flex-col gap-10 px-4 pt-10 pb-20 sm:px-6">
    <header class="flex flex-wrap items-end justify-between gap-5">
      <div class="flex flex-col gap-0.5">
        <h1 class="m-0 text-[40px] leading-tight sm:text-5xl">Your journals</h1>
        <span class="font-hand text-[19px] text-bark"
          >pick a notebook, or tuck in some new pages</span
        >
      </div>
      <KButton variant="second" @click="newJournal = true">
        <template #icon><KIcon name="plus" /></template>
        New journal
      </KButton>
    </header>

    <KEmptyState
      v-if="journals.empty"
      title="Your shelf is empty"
      text="Start a journal, then add photos of its pages."
    >
      <template #illustration><KDoodle name="daisy" /></template>
      <KButton @click="newJournal = true">New journal</KButton>
    </KEmptyState>

    <template v-else>
      <section :aria-labelledby="shelfTitleId" class="flex flex-col gap-4">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <h2 :id="shelfTitleId" class="m-0 text-[22px]">On the shelf</h2>
          <KShelfPager
            v-if="journals.loaded"
            :range="journals.range"
            noun="journals"
            :can-back="journals.canBack && !journals.loading"
            :can-next="journals.canNext && !journals.loading"
            @back="shelfStep('back')"
            @next="shelfStep('next')"
          />
        </div>
        <div class="grid grid-cols-2 gap-6 sm:grid-cols-4">
          <template v-if="journals.loaded">
            <KJournalCover
              v-for="item in journals.shelf"
              :key="item.id"
              :as="RouterLink"
              :to="{ name: 'journal', params: { journalId: item.id } }"
              :name="item.name"
              :meta="plural(item.pageCount, 'page')"
              :color="coverColor(item.id)"
              :selected="item.id === journalId"
            />
          </template>
          <template v-else>
            <KSkeleton v-for="n in 4" :key="n" shape="block" class="h-[132px]" />
          </template>
        </div>
      </section>

      <section v-if="journal" aria-label="Upload pages" class="flex flex-wrap gap-6">
        <KDropzone
          class="min-w-0 flex-[1_1_420px]"
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

      <section v-if="journal" :aria-labelledby="pagesTitleId" class="flex flex-col gap-5">
        <div class="flex flex-wrap items-end justify-between gap-4">
          <div class="flex min-w-0 flex-col gap-1">
            <div class="flex items-center gap-2">
              <h2 :id="pagesTitleId" class="m-0 text-3xl">{{ journal.name }}</h2>
              <KMenu label="Journal actions" :items="menu" align="start" @select="onMenu" />
            </div>
            <p
              v-if="journal.description"
              class="m-0 max-w-[65ch] font-hand text-[19px] whitespace-pre-line text-bark"
            >
              {{ journal.description }}
            </p>
          </div>
          <KFilterChips v-model="filter" label="Filter pages" :options="filters" />
        </div>

        <ul
          v-if="pages.items.length"
          class="m-0 grid list-none grid-cols-[repeat(auto-fill,minmax(190px,1fr))] gap-x-6 gap-y-8 p-0 pt-3"
        >
          <li v-for="(page, index) in pages.items" :key="page.id">
            <PageThumb :page="page" :tilt="tiltFor(index)" @retry="retry" />
          </li>
        </ul>
        <div
          v-else-if="pages.loading"
          class="grid grid-cols-[repeat(auto-fill,minmax(190px,1fr))] gap-x-6 gap-y-8 pt-3"
        >
          <KSkeleton v-for="n in 4" :key="n" shape="block" class="h-[250px]" />
        </div>
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
          @more="pages.more().catch((error) => toastError(error, 'Couldn’t load more pages'))"
        />
      </section>
    </template>

    <JournalDialog v-model:open="newJournal" @created="onCreated" />
    <JournalDialog v-model:open="renaming" :journal="journal" />

    <KDialog
      v-model:open="confirmDelete"
      :title="`Delete ${doomed?.name}?`"
      :description="deleteNote"
    >
      <template #footer>
        <KButton variant="second" autofocus @click="confirmDelete = false">Keep it</KButton>
        <KButton variant="danger" :loading="deleting" @click="deleteJournal">
          Delete journal
        </KButton>
      </template>
    </KDialog>
  </main>
</template>
