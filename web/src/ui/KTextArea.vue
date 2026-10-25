<script setup lang="ts">
import { computed, useId } from 'vue'

import { fieldClass } from './field'
import KFieldShell from './KFieldShell.vue'

defineOptions({ inheritAttrs: false })

const model = defineModel<string>({ default: '' })

const props = withDefaults(
  defineProps<{
    label: string
    rows?: number
    help?: string
    error?: string
    disabled?: boolean
    placeholder?: string
    optional?: boolean
    labelHidden?: boolean
    id?: string
  }>(),
  { rows: 3 },
)

const autoId = useId()
const fieldId = computed(() => props.id ?? autoId)
</script>

<template>
  <KFieldShell
    :id="fieldId"
    v-slot="{ describedby, invalid }"
    :label="label"
    :help="help"
    :error="error"
    :optional="optional"
    :label-hidden="labelHidden"
  >
    <textarea
      :id="fieldId"
      v-model="model"
      v-bind="$attrs"
      :rows="rows"
      :disabled="disabled"
      :placeholder="placeholder"
      :aria-invalid="invalid ? 'true' : undefined"
      :aria-describedby="describedby"
      :class="[fieldClass({ invalid, disabled }), 'resize-y px-4 py-3 leading-normal']"
    />
  </KFieldShell>
</template>
