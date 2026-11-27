<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter, type LocationQuery } from 'vue-router'

import { api, call } from '@/api/client'
import type { Journal, SearchHit, SearchMode } from '@/api/types'
import SearchHitCard from '@/components/SearchHitCard.vue'
import { useRecentSearches } from '@/composables/useRecentSearches'
import { toastError } from '@/utils/notify'
import { matcher, newestFirst } from '@/utils/search'
import { useJournals } from '@/stores/journals'
import {
  KButton,
  KEmptyState,
  KPage,
  KPageHeader,
  KSearchField,
  KSection,
  KSelect,
  KSkeleton,
  KTextField,
  KTip,
} from '@/ui'

const SORTS = ['relevance', 'date', 'words', 'meaning'] as const
type Sort = (typeof SORTS)[number]
const MODES: Record<Sort, SearchMode> = {
  relevance: 'hybrid',
  date: 'hybrid',
  words: 'keyword',
  meaning: 'vector',
}
const LIMIT = 20

interface Search {
  q: string
  sort: Sort
  journalId?: string
  dateFrom?: string
  dateTo?: string
}

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const journals = useJournals()
const { items: recentSearches, add: remember } = useRecentSearches()

function first(value: LocationQuery[string] | undefined): string | undefined {
  const text = Array.isArray(value) ? value[0] : value
  return text?.trim() || undefined
}

// The URL holds the search, so back, reload and shared links bring it back.
const asked = computed<Search>(() => {
  const { query } = route
  const sort = first(query.sort) as Sort | undefined
  return {
    q: first(query.q) ?? '',
    sort: sort && SORTS.includes(sort) ? sort : 'relevance',
    journalId: first(query.journalId),
    dateFrom: first(query.dateFrom),
    dateTo: first(query.dateTo),
  }
})

function go(changes: Partial<Search>, how: 'push' | 'replace' = 'replace') {
  const next = { ...asked.value, ...changes }
  const query = {
    q: next.q || undefined,
    sort: next.sort === 'relevance' ? undefined : next.sort,
    journalId: next.journalId,
    dateFrom: next.dateFrom,
    dateTo: next.dateTo,
  }
  return router[how]({
    name: 'search',
    query: Object.fromEntries(Object.entries(query).filter(([, value]) => value !== undefined)),
  })
}

const text = ref('')
watch(
  () => asked.value.q,
  (q) => (text.value = q),
  { immediate: true },
)

function submit() {
  const q = text.value.trim()
  if (q === asked.value.q) void run()
  else void go({ q }, 'push')
}

function again(q: string) {
  text.value = q
  submit()
}

const hits = ref<SearchHit[]>()
/** What the hits on screen were found with; words about them follow it, not the form. */
const shown = ref<Search>()
const loading = ref(false)
// Bumped by every search, so an answer that's been overtaken is dropped.
let latest = 0

async function run() {
  const mine = ++latest
  const search = asked.value
  if (!search.q) {
    hits.value = shown.value = undefined
    loading.value = false
    return
  }
  remember(search.q)
  loading.value = true
  try {
    const { q, sort, journalId, dateFrom, dateTo } = search
    const result = await call(
      api.GET('/search', {
        params: { query: { q, mode: MODES[sort], journalId, dateFrom, dateTo, limit: LIMIT } },
      }),
    )
    if (mine !== latest) return
    hits.value = result.items
    shown.value = search
  } catch (error) {
    if (mine !== latest) return
    hits.value = shown.value = undefined
    toastError(error, t('search.failed'), {
      retry: run,
      byStatus: {
        502: {
          tone: 'warning',
          detail: t('search.meaningOut'),
          action: {
            label: t('search.byWords'),
            run: () => void go({ sort: 'words' }),
          },
        },
      },
    })
  } finally {
    if (mine === latest) loading.value = false
  }
}

// Relevance and date share one search; only the order differs.
watch(
  () => JSON.stringify({ ...asked.value, sort: MODES[asked.value.sort] }),
  () => void run(),
  { immediate: true },
)

const journalList = ref<Journal[]>([])
onMounted(async () => {
  try {
    journalList.value = await journals.all()
  } catch (error) {
    toastError(error, t('search.journalsFailed'))
  }
})

const journalOptions = computed(() => [
  { value: '', label: t('search.allJournals') },
  ...journalList.value.map((journal) => ({ value: journal.id, label: journal.name })),
])
const sortOptions = computed(() =>
  SORTS.map((value) => ({ value, label: t(`search.sorts.${value}`) })),
)

// The picked sort, once the hits on screen are from its search.
const order = computed(() => {
  const picked = asked.value.sort
  const found = shown.value?.sort
  return found && MODES[found] === MODES[picked] ? picked : found
})
const ordered = computed(() =>
  hits.value && order.value === 'date' ? newestFirst(hits.value) : hits.value,
)
const pattern = computed(() => (shown.value ? matcher(shown.value.q) : undefined))
const blockCount = computed(() => hits.value?.reduce((n, hit) => n + hit.blocks.length, 0) ?? 0)
const filtered = computed(
  () => !!(shown.value?.journalId || shown.value?.dateFrom || shown.value?.dateTo),
)

const journalName = (hit: SearchHit) => journals.byId.get(hit.page.journalId)?.name ?? ''
</script>

<template>
  <KPage>
    <KPageHeader :title="t('search.title')" :subtitle="t('search.subtitle')" />

    <KSearchField
      v-model="text"
      :label="t('search.label')"
      :placeholder="t('search.placeholder')"
      size="lg"
      @search="submit"
    >
      <KButton type="submit" :loading="loading">{{ t('search.submit') }}</KButton>
    </KSearchField>

    <div class="flex flex-wrap items-end gap-x-5 gap-y-3">
      <KSelect
        :label="t('search.journal')"
        :options="journalOptions"
        :model-value="asked.journalId ?? ''"
        class="w-full sm:w-60"
        @update:model-value="go({ journalId: $event || undefined })"
      />
      <KTextField
        type="date"
        :label="t('search.from')"
        :model-value="asked.dateFrom ?? ''"
        :max="asked.dateTo"
        class="w-[calc(50%-10px)] sm:w-44"
        @update:model-value="go({ dateFrom: String($event) || undefined })"
      />
      <KTextField
        type="date"
        :label="t('search.to')"
        :model-value="asked.dateTo ?? ''"
        :min="asked.dateFrom"
        class="w-[calc(50%-10px)] sm:w-44"
        @update:model-value="go({ dateTo: String($event) || undefined })"
      />
      <KSelect
        :label="t('search.sort')"
        :options="sortOptions"
        :model-value="asked.sort"
        class="w-full sm:ml-auto sm:w-48"
        @update:model-value="go({ sort: $event })"
      />
    </div>

    <div class="grid items-start gap-7 lg:grid-cols-[minmax(0,1fr)_280px]">
      <section
        :aria-label="t('search.results')"
        :aria-busy="loading"
        class="flex min-w-0 flex-col gap-4"
      >
        <template v-if="ordered && shown">
          <template v-if="ordered.length">
            <p class="m-0 text-sm text-muted">
              <i18n-t
                :keypath="order === 'relevance' ? 'search.summary' : 'search.summarySorted'"
                scope="global"
              >
                <template #blocks>
                  <strong class="text-ink">{{ t('counts.blocks', blockCount) }}</strong>
                </template>
                <template #pages>{{ t('counts.pages', ordered.length) }}</template>
                <template #order>{{ t(`search.order.${order ?? 'relevance'}`) }}</template>
              </i18n-t>
            </p>
            <ol class="flex flex-col gap-4">
              <li v-for="hit in ordered" :key="hit.page.id">
                <SearchHitCard :hit="hit" :journal="journalName(hit)" :pattern="pattern" />
              </li>
            </ol>
          </template>
          <KEmptyState
            v-else
            :title="t('search.noneTitle', { q: shown.q })"
            :text="filtered ? t('search.noneFiltered') : t('search.none')"
          >
            <KButton
              v-if="filtered"
              variant="second"
              @click="go({ journalId: undefined, dateFrom: undefined, dateTo: undefined })"
            >
              {{ t('search.everywhere') }}
            </KButton>
          </KEmptyState>
        </template>
        <template v-else-if="loading">
          <KSkeleton v-for="n in 3" :key="n" shape="block" class="h-36" />
        </template>
        <KEmptyState
          v-else-if="!asked.q"
          :title="t('search.idleTitle')"
          :text="t('search.idle')"
          doodle="sprig"
        />
      </section>

      <aside class="flex flex-col gap-4">
        <KSection v-if="recentSearches.length" framed :title="t('search.recent')">
          <ul class="flex flex-wrap gap-2">
            <li v-for="item in recentSearches" :key="item">
              <KButton variant="second" size="sm" @click="again(item)">{{ item }}</KButton>
            </li>
          </ul>
        </KSection>
        <KTip :title="t('search.tipTitle')">{{ t('search.tip') }}</KTip>
      </aside>
    </div>
  </KPage>
</template>
