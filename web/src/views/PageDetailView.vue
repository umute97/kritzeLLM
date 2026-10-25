<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import { api, call } from '@/api/client'
import { ApiError } from '@/api/errors'
import { downloadImage, useAuthedImage } from '@/api/images'
import type { Block, Journal, PageDetail } from '@/api/types'
import { formatEntryDates, plural } from '@/lib/format'
import { toastError } from '@/lib/notify'
import { useJournals } from '@/stores/journals'
import { isBusy, usePages } from '@/stores/pages'
import {
  KBanner,
  KBlockCard,
  KBreadcrumb,
  KButton,
  KDialog,
  KDoodle,
  KEmptyState,
  KIcon,
  KMenu,
  KPageStepper,
  KSegmented,
  KSkeleton,
  KSpinner,
  KStatusChip,
  useToasts,
  type MenuItem,
} from '@/ui'

const props = defineProps<{ pageId: string }>()

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
const active = ref<string | null>(null)
const view = ref<'photo' | 'text' | 'both'>('both')
const confirmDelete = ref(false)
const confirmRead = ref(false)
const working = ref<'delete' | 'read' | null>(null)

// The poller in the pages store keeps the status fresh while the page is being read.
const status = computed(() => pages.byId.get(props.pageId)?.status ?? detail.value?.status)
const busy = computed(
  () => status.value !== undefined && isBusy(status.value) && status.value !== 'indexing',
)
const photo = useAuthedImage(() => detail.value?.image.urls.normalized)
const dates = computed(() => (detail.value ? formatEntryDates(detail.value.entryDates) : undefined))

async function load() {
  missing.value = false
  try {
    const page = await call(
      api.GET('/pages/{pageId}', { params: { path: { pageId: props.pageId } } }),
    )
    detail.value = page
    drafts.clear()
    pages.put(page)
    journal.value = await journals.get(page.journalId)
    void findNeighbours(page)
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) missing.value = true
    else toastError(error, 'Couldn’t open this page', load)
  }
}

async function findNeighbours(page: PageDetail) {
  try {
    const all = await pages.journalIndex(page.journalId)
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
    neighbours.value = {}
  }
}

watch(() => props.pageId, load, { immediate: true })

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
  saving.add(block.id)
  try {
    const result = await call(
      api.PATCH('/blocks/{blockId}', { params: { path: { blockId: block.id } }, body }),
    )
    replaceBlock(result.block)
    drafts.delete(block.id)
    saved.add(block.id)
    setTimeout(() => saved.delete(block.id), 2500)
  } catch (error) {
    const what = `Couldn’t save block ${block.seq + 1}`
    if (error instanceof ApiError && error.status === 409) {
      toasts.push({
        tone: 'warning',
        title: what,
        detail: 'This page is still being read. Try again once it’s ready.',
      })
    } else {
      toastError(error, what, () => void patchBlock(block, body))
    }
  } finally {
    saving.delete(block.id)
  }
}

const save = (block: Block) => patchBlock(block, { text: drafts.get(block.id) })
const looksRight = (block: Block) => patchBlock(block, { uncertain: false })

async function readAgain() {
  if (!detail.value) return
  working.value = 'read'
  try {
    await call(
      api.POST('/pages/{pageId}/transcribe', { params: { path: { pageId: props.pageId } } }),
    )
    pages.put({ ...detail.value, status: 'uploaded', error: null })
    confirmRead.value = false
    toasts.push({ tone: 'info', title: `Reading page ${detail.value.pageNumber} again` })
  } catch (error) {
    confirmRead.value = false
    if (error instanceof ApiError && error.status === 409) {
      toasts.push({
        tone: 'info',
        title: 'Already on it',
        detail: 'This page is being read right now.',
      })
    } else {
      toastError(error, 'Couldn’t read the page again')
    }
  } finally {
    working.value = null
  }
}

async function deletePage() {
  if (!detail.value) return
  const { pageNumber, journalId } = detail.value
  working.value = 'delete'
  try {
    await call(api.DELETE('/pages/{pageId}', { params: { path: { pageId: props.pageId } } }))
    pages.remove(props.pageId)
    void journals.refresh(journalId).catch(() => {})
    confirmDelete.value = false
    toasts.push({ tone: 'info', title: `Page ${pageNumber} is gone` })
    await router.push({ name: 'journal', params: { journalId } })
  } catch (error) {
    toastError(error, 'Couldn’t delete the page')
  } finally {
    working.value = null
  }
}

const menu: MenuItem[] = [
  { id: 'read', label: 'Re-transcribe', icon: 'refresh' },
  { id: 'download', label: 'Download photo', icon: 'download' },
  { id: 'delete', label: 'Delete page', icon: 'trash', danger: true },
]

async function onMenu(id: string) {
  if (id === 'read') confirmRead.value = true
  else if (id === 'delete') confirmDelete.value = true
  else if (id === 'download' && detail.value) {
    try {
      await downloadImage(detail.value.image.urls.original, `page-${detail.value.pageNumber}`)
    } catch (error) {
      toastError(error, 'Couldn’t download the photo')
    }
  }
}

function step(id?: string) {
  if (id) void router.push({ name: 'page', params: { pageId: id } })
}
</script>

<template>
  <main class="mx-auto flex max-w-[1200px] flex-col gap-6 px-4 pt-8 pb-20 sm:px-6">
    <KEmptyState
      v-if="missing"
      title="This page wandered off"
      text="It may have been deleted. The rest of the journal is still on the shelf."
    >
      <template #illustration><KDoodle name="squiggle" /></template>
      <KButton :as="RouterLink" to="/">Back to your journals</KButton>
    </KEmptyState>

    <template v-else-if="detail">
      <header class="flex flex-wrap items-end justify-between gap-4">
        <div class="flex flex-col gap-1.5">
          <KBreadcrumb
            :link-as="RouterLink"
            :items="[
              { label: 'Journals', to: '/' },
              {
                label: journal?.name ?? 'Journal',
                to: { name: 'journal', params: { journalId: detail.journalId } },
              },
              { label: `Page ${detail.pageNumber}` },
            ]"
          />
          <div class="flex flex-wrap items-center gap-3.5">
            <h1 class="m-0 text-[40px] leading-tight">Page {{ detail.pageNumber }}</h1>
            <KStatusChip v-if="status" :status="status" />
          </div>
          <span class="text-sm text-muted">
            <template v-if="dates">{{ dates }} · </template
            >{{ plural(detail.blocks.length, 'block') }}
          </span>
        </div>
        <div class="flex flex-wrap items-center gap-2.5">
          <KPageStepper
            :current="detail.pageNumber"
            :total="journal?.pageCount"
            :prev-label="neighbours.prevNumber ? `Page ${neighbours.prevNumber}` : 'Previous page'"
            :next-label="neighbours.nextNumber ? `Page ${neighbours.nextNumber}` : 'Next page'"
            :can-prev="!!neighbours.prev"
            :can-next="!!neighbours.next"
            @prev="step(neighbours.prev)"
            @next="step(neighbours.next)"
          />
          <KButton variant="second" :disabled="busy" @click="confirmRead = true">
            <template #icon><KIcon name="refresh" /></template>
            Re-transcribe
          </KButton>
          <KMenu label="Page actions" :items="menu" @select="onMenu" />
        </div>
      </header>

      <KBanner v-if="status === 'failed'" title="We couldn’t read this page">
        {{
          detail.error?.detail ?? detail.error?.title ?? 'Something went wrong while reading it.'
        }}
        Another try often helps.
        <template #actions>
          <KButton @click="confirmRead = true">Re-transcribe</KButton>
        </template>
      </KBanner>

      <KSegmented
        v-model="view"
        label="Show"
        class="md:hidden"
        :options="[
          { value: 'photo', label: 'Photo' },
          { value: 'text', label: 'Text' },
          { value: 'both', label: 'Both' },
        ]"
      />

      <div class="grid items-start gap-7 md:grid-cols-2">
        <figure :class="['m-0', view === 'text' && 'max-md:hidden']">
          <div
            class="relative overflow-hidden rounded-field border-[1.5px] border-ink bg-paper shadow-[0_8px_0_rgb(180_106_85/0.2)]"
            :style="{ aspectRatio: `${detail.image.width} / ${detail.image.height}` }"
          >
            <img
              v-if="photo"
              :src="photo"
              :alt="`Photo of page ${detail.pageNumber}`"
              class="size-full object-contain"
            />
            <div
              v-else
              class="paper-lines flex size-full items-center justify-center [--line:32px]"
            >
              <KSpinner variant="daisy" :size="48" label="Loading the photo" />
            </div>
          </div>
        </figure>

        <section
          aria-label="Transcribed blocks"
          :class="['flex flex-col gap-3.5', view === 'photo' && 'max-md:hidden']"
        >
          <KBanner v-if="busy" tone="info" title="Still reading this page" icon="book">
            The text shows up here as soon as it’s done.
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
              :active="active === block.id"
              @update:model-value="setText(block, $event)"
              @save="save(block)"
              @undo="drafts.delete(block.id)"
              @confirm="looksRight(block)"
              @activate="active = block.id"
              @deactivate="active = null"
            />
            <KEmptyState
              v-if="detail.blocks.length === 0 && status === 'ready'"
              title="Nothing written here"
              text="This page came back without any text. Re-transcribe it if that looks wrong."
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

    <KDialog
      v-model:open="confirmRead"
      :title="`Read page ${detail?.pageNumber} again?`"
      description="A fresh reading replaces the text, including any fixes you made."
    >
      <template #footer>
        <KButton variant="second" autofocus @click="confirmRead = false">Keep it</KButton>
        <KButton :loading="working === 'read'" @click="readAgain">Read it again</KButton>
      </template>
    </KDialog>

    <KDialog
      v-model:open="confirmDelete"
      :title="`Delete page ${detail?.pageNumber}?`"
      description="The photo and all its text go with it. This can’t be undone."
    >
      <template #footer>
        <KButton variant="second" autofocus @click="confirmDelete = false">Keep it</KButton>
        <KButton variant="danger" :loading="working === 'delete'" @click="deletePage">
          Delete page
        </KButton>
      </template>
    </KDialog>
  </main>
</template>
