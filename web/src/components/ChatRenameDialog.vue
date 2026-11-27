<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { ApiError } from '@/api/errors'
import { useChat } from '@/stores/chat'
import { KButton, KDialog, KTextField } from '@/ui'
import { toastError } from '@/utils/notify'

// Renames a chat. Emptied, it's untitled again until its next question names it.
const props = defineProps<{ conversation?: { id: string; title: string | null } }>()
const open = defineModel<boolean>('open', { default: false })

const { t } = useI18n()
const chat = useChat()
const title = ref('')
const titleError = ref<string>()
const busy = ref(false)

watch(open, (isOpen) => {
  if (!isOpen) return
  title.value = props.conversation?.title ?? ''
  titleError.value = undefined
})

async function save() {
  if (!props.conversation) return
  busy.value = true
  try {
    await chat.rename(props.conversation.id, title.value.trim() || null)
    open.value = false
  } catch (error) {
    const fieldError =
      error instanceof ApiError
        ? error.problem.errors?.find((e) => e.pointer === '/title')?.detail
        : undefined
    if (fieldError) titleError.value = fieldError
    else toastError(error, t('chat.renameFailed'))
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <KDialog
    v-model:open="open"
    :title="t('chat.renameTitle')"
    size="md"
    form
    :dismissible="!busy"
    @submit="save"
  >
    <KTextField
      v-model="title"
      :label="t('chat.name')"
      :help="t('chat.nameHint')"
      maxlength="200"
      autocomplete="off"
      autofocus
      :error="titleError"
    />
    <template #footer>
      <KButton variant="quiet" :disabled="busy" @click="open = false">
        {{ t('chat.cancel') }}
      </KButton>
      <KButton type="submit" :loading="busy">{{ t('chat.save') }}</KButton>
    </template>
  </KDialog>
</template>
