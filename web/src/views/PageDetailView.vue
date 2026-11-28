<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter, type RouteLocationNormalized } from 'vue-router'

import { hasStatus } from '@/api/errors'
import { downloadImage, useAuthedImage } from '@/api/images'
import type { Journal, PageDetail } from '@/api/types'
import LostState from '@/components/LostState.vue'
import { useAction } from '@/composables/useAction'
import { useBlockDrafts } from '@/composables/useBlockDrafts'
import { useConfirm } from '@/composables/useConfirm'
import { useUnsavedGuard } from '@/composables/useUnsavedGuard'
import { formatEntryDates } from '@/utils/format'
import { newestWins } from '@/utils/newest'
import { toastError } from '@/utils/notify'
import { useJournals } from '@/stores/journals'
import { isBusy, usePages, type PageRef } from '@/stores/pages'
import {
  KBanner,
  KBlockCard,
  KBreadcrumb,
  KButton,
  KConfirmDialog,
  KEmptyState,
  KMenu,
  KPage,
  KPageHeader,
  KPager,
  KPhoto,
  KSegmented,
  KSkeleton,
  KStatusChip,
  useToasts,
  type MenuItem,
} from '@/ui'

const props = defineProps<{ pageId: string }>()

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const journals = useJournals()
const pages = usePages()
const toasts = useToasts()

const detail = ref<PageDetail>()
const journal = ref<Journal>()
const missing = ref(false)
const neighbours = ref<{ prev?: PageRef; next?: PageRef }>({})
const active = ref<string | null>(null)
// Blocks a search hit or a source points at: `?blocks=blk_…,blk_…`.
const highlighted = computed(() => new Set(String(route.query.blocks ?? '').split(',')))
const view = ref<'photo' | 'text' | 'both'>('both')
const { drafts, saving, saved, text, setText, save, looksRight } = useBlockDrafts(detail)

// The poller in the pages store keeps the status fresh while the page is being read.
const status = computed(() => pages.byId.get(props.pageId)?.status ?? detail.value?.status)
const busy = computed(
  () => status.value !== undefined && isBusy(status.value) && status.value !== 'indexing',
)
const photo = useAuthedImage(() => detail.value?.image.urls.normalized)
const dates = computed(() => (detail.value ? formatEntryDates(detail.value.entryDates) : undefined))
const meta = computed(() =>
  detail.value
    ? [dates.value, t('counts.blocks', detail.value.blocks.length)].filter(Boolean).join(' · ')
    : undefined,
)

const newest = newestWins()

async function load() {
  const current = newest()
  missing.value = false
  try {
    const page = await pages.fetchDetail(props.pageId)
    if (!current()) return
    detail.value = page
    drafts.clear()
    void nextTick(showHighlighted)
    void findNeighbours(page, current)
    const owner = await journals.get(page.journalId)
    if (current()) journal.value = owner
  } catch (error) {
    if (!current()) return
    if (hasStatus(error, 404)) missing.value = true
    else toastError(error, t('page.openFailed'), { retry: load })
  }
}

function showHighlighted() {
  const block = detail.value?.blocks.find((b) => highlighted.value.has(b.id))
  if (!block) return
  document
    .querySelector(`[data-block-id="${block.id}"]`)
    ?.scrollIntoView?.({ block: 'center', behavior: 'smooth' })
}

async function findNeighbours(page: PageDetail, current: () => boolean) {
  try {
    const found = await pages.neighbours(page)
    if (current()) neighbours.value = found
  } catch {
    if (current()) neighbours.value = {}
  }
}

watch(
  () => props.pageId,
  () => {
    detail.value = undefined
    active.value = null
    neighbours.value = {}
    void load()
  },
  { immediate: true },
)

// Once a fresh reading is done, fetch the new blocks.
watch(status, (now, before) => {
  if (before && now && isBusy(before) && !isBusy(now)) void load()
})

const reading = useConfirm(
  async () => {
    if (!detail.value) return
    await pages.retranscribe(detail.value)
    toasts.push({ tone: 'info', title: t('page.readingAgain', { n: detail.value.pageNumber }) })
  },
  () => ({
    title: t('page.readFailed'),
    byStatus: { 409: { title: t('page.alreadyTitle'), detail: t('page.already') } },
  }),
)

const deleting = useConfirm(
  async () => {
    if (!detail.value) return
    const { pageNumber, journalId } = detail.value
    await pages.remove(detail.value)
    toasts.push({ tone: 'info', title: t('page.deleted', { n: pageNumber }) })
    await router.push({ name: 'journal', params: { journalId } })
  },
  () => ({ title: t('page.deleteFailed') }),
)

const leaving = useConfirm(
  async (to: RouteLocationNormalized) => {
    drafts.clear()
    await router.push(to.fullPath)
  },
  () => ({ title: t('page.leaveFailed') }),
)

useUnsavedGuard(() => drafts.size > 0, leaving.ask)

const download = useAction(
  (page: PageDetail) => downloadImage(page.image.urls.original, `page-${page.pageNumber}`),
  () => ({ title: t('page.downloadFailed') }),
)

const menu = computed<MenuItem[]>(() => [
  { id: 'read', label: t('page.retranscribe'), icon: 'refresh', run: () => reading.ask() },
  {
    id: 'download',
    label: t('page.download'),
    icon: 'download',
    run: () => detail.value && download.run(detail.value),
  },
  {
    id: 'delete',
    label: t('page.delete'),
    icon: 'trash',
    danger: true,
    run: () => deleting.ask(),
  },
])

function step(to?: PageRef) {
  if (to) void router.push({ name: 'page', params: { pageId: to.id } })
}

function pageName(at: PageRef | undefined, fallback: string) {
  return at ? t('common.page', { n: at.pageNumber }) : fallback
}
</script>

<template>
  <KPage>
    <LostState v-if="missing" :title="t('page.lostTitle')" :text="t('page.lost')" />

    <template v-else-if="detail">
      <KPageHeader :title="t('common.page', { n: detail.pageNumber })" :meta="meta">
        <template #eyebrow>
          <KBreadcrumb
            :items="[
              { label: t('page.journals'), to: '/' },
              {
                label: journal?.name ?? t('page.journal'),
                to: { name: 'journal', params: { journalId: detail.journalId } },
              },
              { label: t('common.page', { n: detail.pageNumber }) },
            ]"
          />
        </template>
        <template #title-after>
          <KStatusChip v-if="status" :status="status" />
        </template>
        <template #actions>
          <KPager
            :prev-label="pageName(neighbours.prev, t('page.previous'))"
            :next-label="pageName(neighbours.next, t('page.next'))"
            :can-prev="!!neighbours.prev"
            :can-next="!!neighbours.next"
            @prev="step(neighbours.prev)"
            @next="step(neighbours.next)"
          >
            <span class="font-bold">
              {{ detail.pageNumber
              }}<span v-if="journal?.pageCount" class="font-normal text-muted">
                {{ t('page.of', { n: journal.pageCount }) }}</span
              >
            </span>
          </KPager>
          <KButton variant="second" icon="refresh" :disabled="busy" @click="reading.ask()">
            {{ t('page.retranscribe') }}
          </KButton>
          <KMenu :label="t('page.actions')" :items="menu" />
        </template>
      </KPageHeader>

      <KBanner v-if="status === 'failed'" :title="t('page.failedTitle')">
        {{ detail.error?.detail ?? detail.error?.title ?? t('page.failed') }}
        {{ t('page.anotherTry') }}
        <template #actions>
          <KButton @click="reading.ask()">{{ t('page.retranscribe') }}</KButton>
        </template>
      </KBanner>

      <KSegmented
        v-model="view"
        :label="t('page.show')"
        class="md:hidden"
        :options="[
          { value: 'photo', label: t('page.views.photo') },
          { value: 'text', label: t('page.views.text') },
          { value: 'both', label: t('page.views.both') },
        ]"
      />

      <div class="grid items-start gap-7 md:grid-cols-2">
        <figure :class="['m-0', view === 'text' && 'max-md:hidden']">
          <KPhoto
            :src="photo"
            :alt="t('page.photoAlt', { n: detail.pageNumber })"
            :width="detail.image.width"
            :height="detail.image.height"
            fit="contain"
            :loading-label="t('page.loadingPhoto')"
            class="rounded-field border-[1.5px] border-ink shadow-pin [--line:32px]"
          />
        </figure>

        <section
          :aria-label="t('page.blocks')"
          :class="['flex flex-col gap-3.5', view === 'photo' && 'max-md:hidden']"
        >
          <KBanner v-if="busy" tone="info" :title="t('page.readingTitle')" icon="book">
            {{ t('page.reading') }}
          </KBanner>
          <template v-else>
            <KBlockCard
              v-for="(block, index) in detail.blocks"
              :key="block.id"
              :model-value="text(block)"
              :seq="index + 1"
              :kind="block.kind"
              :uncertain="block.uncertain"
              :dirty="drafts.has(block.id)"
              :saving="saving.has(block.id)"
              :saved="saved.has(block.id)"
              :selected="active === block.id || highlighted.has(block.id)"
              :data-block-id="block.id"
              @update:model-value="setText(block, $event)"
              @save="save(block)"
              @undo="drafts.delete(block.id)"
              @confirm="looksRight(block)"
              @activate="active = block.id"
              @deactivate="active = null"
            />
            <KEmptyState
              v-if="detail.blocks.length === 0 && status === 'ready'"
              :title="t('page.emptyTitle')"
              :text="t('page.empty')"
            />
          </template>
        </section>
      </div>
    </template>

    <div v-else class="grid gap-7 md:grid-cols-2">
      <KSkeleton shape="block" class="h-[520px]" />
      <div class="flex flex-col gap-3.5">
        <KSkeleton v-for="n in 4" :key="n" shape="block" class="h-24" />
      </div>
    </div>

    <KConfirmDialog
      v-model:open="reading.open"
      :title="t('page.readAgainTitle', { n: detail?.pageNumber })"
      :description="t('page.readAgain')"
      :confirm-label="t('page.readAgainConfirm')"
      tone="main"
      :loading="reading.busy"
      @confirm="reading.run()"
    />
    <KConfirmDialog
      v-model:open="deleting.open"
      :title="t('page.deleteTitle', { n: detail?.pageNumber })"
      :description="t('page.deleteNote')"
      :confirm-label="t('page.delete')"
      :loading="deleting.busy"
      @confirm="deleting.run()"
    />
    <KConfirmDialog
      v-model:open="leaving.open"
      :title="t('page.leaveTitle')"
      :description="t('page.leave', { blocks: t('counts.blocks', drafts.size) })"
      :confirm-label="t('page.leaveConfirm')"
      :loading="leaving.busy"
      @confirm="leaving.run()"
    />
  </KPage>
</template>
