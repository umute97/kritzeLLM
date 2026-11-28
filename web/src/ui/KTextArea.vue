<script setup lang="ts">
import { joinIds, useSplitAttrs } from './attrs'
import KFieldShell from './KFieldShell.vue'
import { fieldClass } from './styles'

defineOptions({ inheritAttrs: false })

const model = defineModel<string>({ default: '' })

withDefaults(
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

const { rootAttrs, controlAttrs } = useSplitAttrs()
</script>

<template>
  <KFieldShell
    v-bind="rootAttrs()"
    :id="id"
    v-slot="{ id: fieldId, describedby, invalid }"
    :label="label"
    :help="help"
    :error="error"
    :optional="optional"
    :label-hidden="labelHidden"
  >
    <textarea
      :id="fieldId"
      v-model="model"
      v-bind="controlAttrs()"
      :rows="rows"
      :disabled="disabled"
      :placeholder="placeholder"
      :aria-invalid="invalid ? 'true' : undefined"
      :aria-describedby="joinIds(describedby, $attrs['aria-describedby'])"
      :class="[fieldClass({ invalid, disabled }), 'resize-y px-4 py-3 leading-normal']"
    />
  </KFieldShell>
</template>
