<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { ApiError } from '@/api/errors'
import type { Journal } from '@/api/types'
import { toastError } from '@/utils/notify'
import { useJournals } from '@/stores/journals'
import { KButton, KDialog, KDoodle, KTextArea, KTextField } from '@/ui'

// Makes a new journal, or renames `journal` when one is given.
const props = defineProps<{ journal?: Journal }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ created: [journal: Journal] }>()

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
    nameError.value = 'Give it a name, even a tiny one'
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
      toastError(error, editing.value ? 'Couldn’t rename the journal' : 'Couldn’t make the journal')
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <KDialog
    v-model:open="open"
    :title="editing ? 'Rename journal' : 'A new journal'"
    width="md"
    form
    :dismissible="!busy"
    @submit="save"
  >
    <template #decoration>
      <KDoodle name="sprig" :size="46" class="absolute -top-5 right-7" />
    </template>
    <div class="flex flex-col gap-3.5">
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
    </div>
    <template #footer>
      <KButton variant="quiet" :disabled="busy" @click="open = false">Cancel</KButton>
      <KButton type="submit" :loading="busy">
        {{ editing ? 'Save' : 'Create journal' }}
      </KButton>
    </template>
  </KDialog>
</template>
