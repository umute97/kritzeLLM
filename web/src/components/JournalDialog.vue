<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { ApiError } from '@/api/errors'
import type { Journal } from '@/api/types'
import { toastError } from '@/utils/notify'
import { useJournals } from '@/stores/journals'
import { KButton, KDialog, KTextArea, KTextField } from '@/ui'

// Makes a new journal, or renames `journal` when one is given.
const props = defineProps<{ journal?: Journal }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ created: [journal: Journal] }>()

const { t } = useI18n()
const journals = useJournals()
const name = ref('')
const description = ref('')
const nameError = ref<string>()
const busy = ref(false)

const editing = computed(() => props.journal !== undefined)

watch(open, (isOpen) => {
  if (!isOpen) return
  name.value = props.journal?.name ?? ''
  description.value = props.journal?.description ?? ''
  nameError.value = undefined
})

async function save() {
  if (!name.value.trim()) {
    nameError.value = t('journalDialog.nameMissing')
    return
  }
  busy.value = true
  try {
    const fields = { name: name.value.trim(), description: description.value.trim() || null }
    if (props.journal) {
      await journals.update(props.journal.id, fields)
      open.value = false
    } else {
      const journal = await journals.create(fields.name, fields.description)
      open.value = false
      emit('created', journal)
    }
  } catch (error) {
    const fieldError =
      error instanceof ApiError
        ? error.problem.errors?.find((e) => e.pointer === '/name')?.detail
        : undefined
    if (fieldError) nameError.value = fieldError
    else
      toastError(
        error,
        editing.value ? t('journalDialog.renameFailed') : t('journalDialog.createFailed'),
      )
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <KDialog
    v-model:open="open"
    :title="editing ? t('journalDialog.renameTitle') : t('journalDialog.newTitle')"
    size="md"
    form
    :dismissible="!busy"
    doodle="sprig"
    @submit="save"
  >
    <div class="flex flex-col gap-3.5">
      <KTextField
        v-model="name"
        :label="t('journalDialog.name')"
        :placeholder="t('journalDialog.namePlaceholder')"
        autocomplete="off"
        :error="nameError"
      />
      <KTextArea
        v-model="description"
        :label="t('journalDialog.description')"
        optional
        :rows="2"
        :placeholder="t('journalDialog.descriptionPlaceholder')"
      />
    </div>
    <template #footer>
      <KButton variant="quiet" :disabled="busy" @click="open = false">
        {{ t('journalDialog.cancel') }}
      </KButton>
      <KButton type="submit" :loading="busy">
        {{ editing ? t('journalDialog.save') : t('journalDialog.create') }}
      </KButton>
    </template>
  </KDialog>
</template>
