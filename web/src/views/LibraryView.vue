<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

import { hasStatus } from '@/api/errors'
import type { Journal, Page } from '@/api/types'
import JournalDialog from '@/components/JournalDialog.vue'
import PageThumb from '@/components/PageThumb.vue'
import UploadBatch from '@/components/UploadBatch.vue'
import { useAction } from '@/composables/useAction'
import { useConfirm } from '@/composables/useConfirm'
import { coverColor } from '@/utils/covers'
import { fileSize } from '@/utils/format'
import { toastError } from '@/utils/notify'
import { MAX_BYTES, PHOTO_ACCEPT } from '@/utils/photos'
import { PER_SHELF, useJournals } from '@/stores/journals'
import { usePages } from '@/stores/pages'
import { useUploads } from '@/stores/uploads'
import {
  KAddTile,
  KButton,
  KCardGrid,
  KConfirmDialog,
  KDropTarget,
  KEmptyState,
  KFileButton,
  KIconButton,
  KJournalCover,
  KLoadMore,
  KPage,
  KPageHeader,
  KPager,
  KSection,
  KSelect,
  KTooltip,
  tiltFor,
  useToasts,
} from '@/ui'

const props = defineProps<{ journalId?: string }>()

const { t } = useI18n()
const router = useRouter()
const journals = useJournals()
const pages = usePages()
const uploads = useUploads()
const toasts = useToasts()

type Filter = 'all' | 'ready' | 'failed'
const filters = computed(() =>
  (['all', 'ready', 'failed'] as const).map((value) => ({
    value,
    label: t(`library.filters.${value}`),
  })),
)
const filter = ref<Filter>('all')
const newJournal = ref(false)
const renaming = ref(false)

const journal = computed(() => (props.journalId ? journals.byId.get(props.journalId) : undefined))
const batch = computed(() => (journal.value ? uploads.batch(journal.value.id) : undefined))
const roomOnShelf = computed(
  () => journals.loaded && !journals.canNext && journals.shelf.length < PER_SHELF,
)
const range = computed(() => {
  const first = journals.index * PER_SHELF + 1
  return t('library.range', { first, last: first + journals.shelf.length - 1 })
})

async function openShelf() {
  try {
    if (!journals.loaded) await journals.show(0)
    if (!props.journalId && journals.shelf[0]) {
      await router.replace({ name: 'journal', params: { journalId: journals.shelf[0].id } })
    }
  } catch (error) {
    toastError(error, t('library.openFailed'), { retry: openShelf })
  }
}

async function loadPages() {
  if (!props.journalId) return
  try {
    await journals.get(props.journalId)
    await pages.load(props.journalId, filter.value === 'all' ? undefined : filter.value)
  } catch (error) {
    if (hasStatus(error, 404)) {
      toasts.push({ tone: 'info', title: t('library.goneTitle'), detail: t('library.gone') })
      await router.replace({ name: 'library' })
      return
    }
    toastError(error, t('library.loadFailed'), { retry: loadPages })
  }
}

onMounted(openShelf)
watch([() => props.journalId, filter], loadPages, { immediate: true })

const shelfStep = useAction(
  (step: 'back' | 'next') => journals[step](),
  () => ({ title: t('library.turnFailed') }),
)
const retry = useAction(
  (page: Page) => pages.retranscribe(page),
  (page) => ({ title: t('library.retryFailed', { n: page.pageNumber }) }),
)
const more = useAction(
  () => pages.more(),
  () => ({ title: t('library.moreFailed') }),
)

function onFiles(files: File[]) {
  if (!journal.value) return
  const refused = uploads.add(journal.value.id, files)
  if (!refused) return
  const { file, reason } = refused
  toasts.push({
    tone: 'error',
    title: t(reason === 'size' ? 'uploads.isTooBig' : 'uploads.isNotPhoto', { name: file.name }),
    detail: t('library.rejected', {
      photosOnly: t('uploads.notPhotoNote'),
      limit: fileSize(MAX_BYTES),
    }),
  })
}

function onCreated(created: Journal) {
  toasts.push({
    tone: 'success',
    title: t('library.createdTitle'),
    detail: t('library.created', { name: created.name }),
  })
  void router.push({ name: 'journal', params: { journalId: created.id } })
}

// Photos still going up would land in a journal that's gone.
const canDelete = computed(() => !batch.value?.active)

const deleting = useConfirm(
  async (gone: Journal) => {
    await journals.remove(gone.id)
    toasts.push({ tone: 'info', title: t('library.deleted', { name: gone.name }) })
    const first = journals.shelf[0]
    await router.replace(
      first ? { name: 'journal', params: { journalId: first.id } } : { name: 'library' },
    )
  },
  () => ({ title: t('library.deleteFailed') }),
)

const deleteNote = computed(() => {
  const count = deleting.subject?.pageCount ?? 0
  return count
    ? t('library.deletePages', { pages: t('counts.pages', count) })
    : t('library.deleteEmpty')
})

// The list on screen can trail the picked filter while the new one loads; words follow the list.
const shownFilter = computed(() => pages.view?.status ?? 'all')

const summary = computed(() => {
  const shown = pages.items.length
  if (shownFilter.value === 'all' && journal.value) {
    return t('library.showing', { shown, total: t('counts.pages', journal.value.pageCount) })
  }
  return t(shownFilter.value === 'ready' ? 'library.showingReady' : 'library.showingFailed', shown)
})
</script>

<template>
  <KPage gap="lg">
    <KPageHeader :title="t('library.title')" :subtitle="t('library.subtitle')">
      <template #actions>
        <KPager
          v-if="journals.loaded && !journals.empty"
          text-first
          :prev-label="t('library.previous')"
          :next-label="t('library.more')"
          :can-prev="journals.canBack && !journals.loading"
          :can-next="journals.canNext && !journals.loading"
          @prev="shelfStep.run('back')"
          @next="shelfStep.run('next')"
        >
          <span class="text-sm text-muted">{{ range }}</span>
        </KPager>
        <KButton variant="second" icon="plus" @click="newJournal = true">
          {{ t('library.newJournal') }}
        </KButton>
      </template>
    </KPageHeader>

    <KEmptyState
      v-if="journals.empty"
      :title="t('library.emptyTitle')"
      :text="t('library.empty')"
      doodle="daisy"
    >
      <KButton @click="newJournal = true">{{ t('library.newJournal') }}</KButton>
    </KEmptyState>

    <template v-else>
      <KCardGrid kind="covers" :loading="!journals.loaded">
        <li v-for="item in journals.shelf" :key="item.id">
          <KJournalCover
            :to="{ name: 'journal', params: { journalId: item.id } }"
            :name="item.name"
            :meta="t('counts.pages', item.pageCount)"
            :color="coverColor(item.id)"
            :selected="item.id === journalId"
          />
        </li>
        <li v-if="roomOnShelf">
          <KAddTile :label="t('library.newJournal')" @click="newJournal = true" />
        </li>
      </KCardGrid>

      <KDropTarget v-if="journal" :count-label="(n) => t('counts.photos', n)" @files="onFiles">
        <KSection
          :title="journal.name"
          :description="journal.description ?? undefined"
          size="lg"
          align="end"
        >
          <template #title-after>
            <KTooltip :text="t('library.rename')">
              <KIconButton
                icon="pencil"
                :label="t('library.rename')"
                variant="quiet"
                size="sm"
                @click="renaming = true"
              />
            </KTooltip>
            <KTooltip
              v-slot="{ describedby }"
              :text="canDelete ? t('library.delete') : t('library.stillUploading')"
            >
              <KIconButton
                icon="trash"
                :label="t('library.delete')"
                variant="quiet"
                size="sm"
                :disabled="!canDelete"
                :aria-describedby="canDelete ? undefined : describedby"
                @click="deleting.ask(journal)"
              />
            </KTooltip>
          </template>
          <template #aside>
            <KSelect v-model="filter" :label="t('library.show')" label-hidden :options="filters" />
            <KFileButton :accept="PHOTO_ACCEPT" @files="onFiles">
              {{ t('library.addPhotos') }}
            </KFileButton>
          </template>

          <UploadBatch
            v-if="batch?.rows.length"
            :key="journal.id"
            :batch="batch"
            :journal-name="journal.name"
            @clear="uploads.clear(journal.id)"
          />
          <KCardGrid
            kind="pages"
            :loading="!pages.view && pages.loading"
            :empty="!pages.items.length"
          >
            <li v-for="(page, index) in pages.items" :key="page.id">
              <PageThumb :page="page" :tilt="tiltFor(index)" @retry="retry.run" />
            </li>
            <template #empty>
              <KEmptyState
                v-if="shownFilter !== 'all'"
                :title="t('library.calmTitle')"
                :text="shownFilter === 'failed' ? t('library.noneFailed') : t('library.noneReady')"
              >
                <KButton variant="second" @click="filter = 'all'">
                  {{ t('library.showAll') }}
                </KButton>
              </KEmptyState>
              <KEmptyState
                v-else
                :title="t('library.noPagesTitle')"
                :text="t('library.noPages', { name: journal.name })"
              />
            </template>
          </KCardGrid>

          <KLoadMore
            v-if="pages.view"
            :summary="summary"
            :has-more="pages.nextCursor !== null"
            :loading="pages.loading"
            :label="t('library.showMore')"
            @more="more.run()"
          />
        </KSection>
      </KDropTarget>
    </template>

    <JournalDialog v-model:open="newJournal" @created="onCreated" />
    <JournalDialog v-model:open="renaming" :journal="journal" />

    <KConfirmDialog
      v-model:open="deleting.open"
      :title="t('library.deleteTitle', { name: deleting.subject?.name })"
      :description="deleteNote"
      :confirm-label="t('library.delete')"
      :loading="deleting.busy"
      @confirm="deleting.run()"
    />
  </KPage>
</template>
