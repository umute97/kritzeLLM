<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { useFormDialog } from '@/composables/useFormDialog'
import { useChat } from '@/stores/chat'
import { KButton, KDialog, KTextField } from '@/ui'

// Renames a chat. Emptied, it's untitled again until its next question names it.
const props = defineProps<{ conversation?: { id: string; title: string | null } }>()
const open = defineModel<boolean>('open', { default: false })

const { t } = useI18n()
const chat = useChat()
const title = ref('')

const form = useFormDialog(open, {
  pointer: '/title',
  fill: () => (title.value = props.conversation?.title ?? ''),
  async save() {
    if (props.conversation) await chat.rename(props.conversation.id, title.value.trim() || null)
  },
  failed: () => t('chat.renameFailed'),
})
</script>

<template>
  <KDialog
    v-model:open="open"
    :title="t('chat.renameTitle')"
    size="md"
    form
    :dismissible="!form.busy"
    @submit="form.submit()"
  >
    <KTextField
      v-model="title"
      :label="t('common.name')"
      :help="t('chat.nameHint')"
      maxlength="200"
      autocomplete="off"
      autofocus
      :error="form.error"
    />
    <template #footer>
      <KButton variant="quiet" :disabled="form.busy" @click="open = false">
        {{ t('common.cancel') }}
      </KButton>
      <KButton type="submit" :loading="form.busy">{{ t('common.save') }}</KButton>
    </template>
  </KDialog>
</template>
