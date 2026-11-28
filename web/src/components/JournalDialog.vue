<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'

import type { Journal } from '@/api/types'
import { useFormDialog } from '@/composables/useFormDialog'
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

const form = useFormDialog(open, {
  pointer: '/name',
  fill() {
    name.value = props.journal?.name ?? ''
    description.value = props.journal?.description ?? ''
  },
  async save() {
    const fields = { name: name.value.trim(), description: description.value.trim() || null }
    if (props.journal) await journals.update(props.journal.id, fields)
    else emit('created', await journals.create(fields.name, fields.description))
  },
  failed: () => t(props.journal ? 'journalDialog.renameFailed' : 'journalDialog.createFailed'),
})

function submit() {
  if (name.value.trim()) void form.submit()
  else form.error = t('journalDialog.nameMissing')
}
</script>

<template>
  <KDialog
    v-model:open="open"
    :title="journal ? t('journalDialog.renameTitle') : t('journalDialog.newTitle')"
    size="md"
    form
    :dismissible="!form.busy"
    doodle="sprig"
    @submit="submit"
  >
    <div class="flex flex-col gap-3.5">
      <KTextField
        v-model="name"
        :label="t('common.name')"
        :placeholder="t('journalDialog.namePlaceholder')"
        autocomplete="off"
        :error="form.error"
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
      <KButton variant="quiet" :disabled="form.busy" @click="open = false">
        {{ t('common.cancel') }}
      </KButton>
      <KButton type="submit" :loading="form.busy">
        {{ journal ? t('common.save') : t('journalDialog.create') }}
      </KButton>
    </template>
  </KDialog>
</template>
