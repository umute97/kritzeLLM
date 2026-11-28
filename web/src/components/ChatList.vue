<script setup lang="ts">
import { ref, useId, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import type { Conversation } from '@/api/types'
import { KButton, KDisclosure, KListLink } from '@/ui'
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
const listId = useId()

watch(
  () => props.current,
  () => (unfolded.value = false),
)
</script>

<template>
  <nav :aria-label="t('chat.earlier')" class="flex flex-col gap-4">
    <KButton variant="second" icon="plus" :to="{ name: 'chat' }">{{ t('chat.newChat') }}</KButton>
    <h2 class="m-0 text-xl">
      <KDisclosure v-model:open="unfolded" :controls="listId" size="md" class="lg:hidden">
        {{ t('chat.earlier') }}
      </KDisclosure>
      <span class="hidden lg:inline">{{ t('chat.earlier') }}</span>
    </h2>
    <div :id="listId" :class="['flex-col gap-3 lg:flex', unfolded ? 'flex' : 'hidden']">
      <ul v-if="chats.length" class="flex flex-col gap-1.5">
        <li v-for="chat in chats" :key="chat.id">
          <KListLink
            :to="{ name: 'chat', params: { conversationId: chat.id } }"
            :title="chat.title ?? t('chat.untitled')"
            :meta="formatRecent(chat.updatedAt)"
            :current="chat.id === current"
          />
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
