<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'

import type { Conversation } from '@/api/types'
import { KButton, KIcon } from '@/ui'
import { formatRecent } from '@/utils/format'

// Earlier chats, most recently active first. On phones they fold away behind a toggle.
const props = defineProps<{
  chats: Conversation[]
  current?: string
  hasMore: boolean
  loading: boolean
}>()

const emit = defineEmits<{ more: [] }>()

const { t } = useI18n()
const unfolded = ref(false)

watch(
  () => props.current,
  () => (unfolded.value = false),
)
</script>

<template>
  <nav :aria-label="t('chat.earlier')" class="flex flex-col gap-4">
    <KButton variant="second" icon="plus" :to="{ name: 'chat' }">{{ t('chat.newChat') }}</KButton>
    <h2 class="m-0 text-xl">
      <button
        type="button"
        :aria-expanded="unfolded"
        class="flex cursor-pointer items-center gap-1.5 lg:hidden"
        @click="unfolded = !unfolded"
      >
        {{ t('chat.earlier') }}
        <KIcon name="chevron-down" :size="16" :class="unfolded && 'rotate-180'" />
      </button>
      <span class="hidden lg:inline">{{ t('chat.earlier') }}</span>
    </h2>
    <div :class="['flex-col gap-3 lg:flex', unfolded ? 'flex' : 'hidden']">
      <ul v-if="chats.length" class="flex flex-col gap-1.5">
        <li v-for="chat in chats" :key="chat.id">
          <RouterLink
            :to="{ name: 'chat', params: { conversationId: chat.id } }"
            :aria-current="chat.id === current ? 'page' : undefined"
            :class="[
              'flex flex-col gap-0.5 rounded-[14px] border-[1.5px] px-3 py-2.5 text-ink no-underline',
              chat.id === current ? 'border-ink bg-paper' : 'border-transparent hover:bg-paper/60',
            ]"
          >
            <strong class="truncate text-[15px]">{{ chat.title ?? t('chat.untitled') }}</strong>
            <span class="text-[13px] text-muted">{{ formatRecent(chat.updatedAt) }}</span>
          </RouterLink>
        </li>
      </ul>
      <p v-else-if="!loading" class="m-0 text-sm text-muted">{{ t('chat.noChats') }}</p>
      <KButton
        v-if="hasMore"
        variant="quiet"
        size="sm"
        :loading="loading"
        class="self-start"
        @click="emit('more')"
      >
        {{ t('chat.olderChats') }}
      </KButton>
    </div>
  </nav>
</template>
