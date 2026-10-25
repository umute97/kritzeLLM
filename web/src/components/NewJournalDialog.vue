<script setup lang="ts">
import { ref, watch } from 'vue'

import { ApiError } from '@/api/errors'
import type { Journal } from '@/api/types'
import { toastError } from '@/lib/notify'
import { useJournals } from '@/stores/journals'
import { KButton, KDialog, KDoodle, KTextArea, KTextField } from '@/ui'

const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ created: [journal: Journal] }>()

const journals = useJournals()
const name = ref('')
const description = ref('')
const nameError = ref<string>()
const busy = ref(false)

watch(open, (isOpen) => {
  if (!isOpen) return
  name.value = ''
  description.value = ''
  nameError.value = undefined
})

async function create() {
  if (!name.value.trim()) {
    nameError.value = 'Give it a name, even a tiny one'
    return
  }
  busy.value = true
  try {
    const journal = await journals.create(name.value.trim(), description.value.trim() || null)
    open.value = false
    emit('created', journal)
  } catch (error) {
    const fieldError =
      error instanceof ApiError
        ? error.problem.errors?.find((e) => e.pointer === '/name')?.detail
        : undefined
    if (fieldError) nameError.value = fieldError
    else toastError(error, 'Couldn’t make the journal')
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <KDialog v-model:open="open" title="A new journal" width="md">
    <template #decoration>
      <KDoodle name="sprig" :size="46" class="absolute -top-12 right-0" />
    </template>
    <form id="new-journal" class="flex flex-col gap-3.5" novalidate @submit.prevent="create">
      <KTextField
        v-model="name"
        label="Name"
        placeholder="Summer sketchbook"
        autocomplete="off"
        :error="nameError"
      />
      <KTextArea
        v-model="description"
        label="Description"
        optional
        :rows="2"
        placeholder="What lives in this notebook?"
      />
    </form>
    <template #footer>
      <KButton variant="quiet" @click="open = false">Cancel</KButton>
      <KButton type="submit" form="new-journal" :loading="busy">Create journal</KButton>
    </template>
  </KDialog>
</template>
