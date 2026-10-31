<script setup lang="ts">
import { computed, onUnmounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  onBeforeRouteLeave,
  onBeforeRouteUpdate,
  useRouter,
  type RouteLocationNormalized,
} from 'vue-router'

import { api, call } from '@/api/client'
import { ApiError } from '@/api/errors'
import { downloadImage, useAuthedImage } from '@/api/images'
import type { Block, Journal, PageDetail } from '@/api/types'
import LostState from '@/components/LostState.vue'
import { useAction } from '@/composables/useAction'
import { useConfirm } from '@/composables/useConfirm'
import { formatEntryDates } from '@/utils/format'
import { toastError } from '@/utils/notify'
import { useJournals } from '@/stores/journals'
import { isBusy, usePages } from '@/stores/pages'
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
const router = useRouter()
const journals = useJournals()
const pages = usePages()
const toasts = useToasts()

const detail = ref<PageDetail>()
const journal = ref<Journal>()
const missing = ref(false)
const neighbours = ref<{ prev?: string; next?: string; prevNumber?: number; nextNumber?: number }>(
  {},
)

const drafts = reactive(new Map<string, string>())
const saving = reactive(new Set<string>())
const saved = reactive(new Set<string>())
const savedTimers = new Map<string, ReturnType<typeof setTimeout>>()
const active = ref<string | null>(null)
const view = ref<'photo' | 'text' | 'both'>('both')
const reading = useConfirm()
const deleting = useConfirm()
const leaving = useConfirm<RouteLocationNormalized>()

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

// Bumped by every load, so an answer for a page you've already paged past is dropped.
let latest = 0

async function load() {
  const mine = ++latest
  missing.value = false
  try {
    const page = await call(
      api.GET('/pages/{pageId}', { params: { path: { pageId: props.pageId } } }),
    )
    if (mine !== latest) return
    detail.value = page
    drafts.clear()
    pages.put(page)
    void findNeighbours(page, mine)
    const owner = await journals.get(page.journalId)
    if (mine === latest) journal.value = owner
  } catch (error) {
    if (mine !== latest) return
    if (error instanceof ApiError && error.status === 404) missing.value = true
    else toastError(error, t('page.openFailed'), { retry: load })
  }
}

async function findNeighbours(page: PageDetail, mine: number) {
  try {
    const all = await pages.journalIndex(page.journalId)
    if (mine !== latest) return
    const at = all.findIndex((p) => p.id === page.id)
    const prev = all[at - 1]
    const next = all[at + 1]
    neighbours.value = {
      prev: prev?.id,
      next: next?.id,
      prevNumber: prev?.pageNumber,
      nextNumber: next?.pageNumber,
    }
  } catch {
    if (mine === latest) neighbours.value = {}
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

function text(block: Block): string {
  return drafts.get(block.id) ?? block.text
}

function setText(block: Block, value: string) {
  if (value === block.text) drafts.delete(block.id)
  else drafts.set(block.id, value)
}

function replaceBlock(updated: Block) {
  if (!detail.value) return
  detail.value = {
    ...detail.value,
    blocks: detail.value.blocks.map((b) => (b.id === updated.id ? updated : b)),
  }
}

async function patchBlock(block: Block, body: { text?: string; uncertain?: boolean }) {
  if (saving.has(block.id)) return
  saving.add(block.id)
  try {
    const result = await call(
      api.PATCH('/blocks/{blockId}', { params: { path: { blockId: block.id } }, body }),
    )
    replaceBlock(result.block)
    // Whatever was typed while it saved stays a draft on top of the saved text.
    if (drafts.get(block.id) === result.block.text) drafts.delete(block.id)
    saved.add(block.id)
    clearTimeout(savedTimers.get(block.id))
    savedTimers.set(
      block.id,
      setTimeout(() => saved.delete(block.id), 2500),
    )
  } catch (error) {
    toastError(error, t('page.saveFailed', { n: block.seq + 1 }), {
      retry: () => void patchBlock(block, body),
      byStatus: {
        409: {
          tone: 'warning',
          detail: t('page.busy'),
        },
      },
    })
  } finally {
    saving.delete(block.id)
  }
}

function save(block: Block) {
  const draft = drafts.get(block.id)
  if (draft === undefined) return
  if (!draft.trim()) {
    toasts.push({
      tone: 'info',
      title: t('page.blockEmptyTitle'),
      detail: t('page.blockEmpty'),
    })
    return
  }
  return patchBlock(block, { text: draft })
}

const looksRight = (block: Block) => patchBlock(block, { uncertain: false })

function readAgain() {
  return reading.run(
    async () => {
      if (!detail.value) return
      await pages.retranscribe(detail.value)
      toasts.push({ tone: 'info', title: t('page.readingAgain', { n: detail.value.pageNumber }) })
    },
    {
      title: t('page.readFailed'),
      byStatus: { 409: { title: t('page.alreadyTitle'), detail: t('page.already') } },
    },
  )
}

function deletePage() {
  return deleting.run(
    async () => {
      if (!detail.value) return
      const { pageNumber, journalId } = detail.value
      await call(api.DELETE('/pages/{pageId}', { params: { path: { pageId: props.pageId } } }))
      pages.remove(props.pageId)
      void journals.refresh(journalId).catch(() => {})
      toasts.push({ tone: 'info', title: t('page.deleted', { n: pageNumber }) })
      await router.push({ name: 'journal', params: { journalId } })
    },
    { title: t('page.deleteFailed') },
  )
}

const download = useAction(
  (page: PageDetail) => downloadImage(page.image.urls.original, `page-${page.pageNumber}`),
  { title: () => t('page.downloadFailed') },
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

function step(id?: string) {
  if (id) void router.push({ name: 'page', params: { pageId: id } })
}

function holdUnsaved(to: RouteLocationNormalized) {
  if (drafts.size === 0) return true
  leaving.ask(to)
  return false
}

onBeforeRouteLeave(holdUnsaved)
onBeforeRouteUpdate(holdUnsaved)

function leave() {
  return leaving.run(
    async (to) => {
      drafts.clear()
      await router.push(to.fullPath)
    },
    { title: t('page.leaveFailed') },
  )
}

function holdUnload(event: BeforeUnloadEvent) {
  if (drafts.size > 0) event.preventDefault()
}

window.addEventListener('beforeunload', holdUnload)

onUnmounted(() => {
  window.removeEventListener('beforeunload', holdUnload)
  savedTimers.forEach(clearTimeout)
})
</script>

<template>
  <KPage>
    <LostState v-if="missing" :title="t('page.lostTitle')" :text="t('page.lost')" />

    <template v-else-if="detail">
      <KPageHeader :title="t('page.title', { n: detail.pageNumber })" :meta="meta">
        <template #eyebrow>
          <KBreadcrumb
            :items="[
              { label: t('page.journals'), to: '/' },
              {
                label: journal?.name ?? t('page.journal'),
                to: { name: 'journal', params: { journalId: detail.journalId } },
              },
              { label: t('page.title', { n: detail.pageNumber }) },
            ]"
          />
        </template>
        <template #title-after>
          <KStatusChip v-if="status" :status="status" />
        </template>
        <template #actions>
          <KPager
            :prev-label="
              neighbours.prevNumber
                ? t('page.title', { n: neighbours.prevNumber })
                : t('page.previous')
            "
            :next-label="
              neighbours.nextNumber ? t('page.title', { n: neighbours.nextNumber }) : t('page.next')
            "
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
              :selected="active === block.id"
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
      @confirm="readAgain"
    />
    <KConfirmDialog
      v-model:open="deleting.open"
      :title="t('page.deleteTitle', { n: detail?.pageNumber })"
      :description="t('page.deleteNote')"
      :confirm-label="t('page.delete')"
      :loading="deleting.busy"
      @confirm="deletePage"
    />
    <KConfirmDialog
      v-model:open="leaving.open"
      :title="t('page.leaveTitle')"
      :description="t('page.leave', { blocks: t('counts.blocks', drafts.size) })"
      :confirm-label="t('page.leaveConfirm')"
      :loading="leaving.busy"
      @confirm="leave"
    />
  </KPage>
</template>
