<script setup lang="ts">
import { computed, useId } from 'vue'

import { fieldClass } from './field'
import KFieldShell from './KFieldShell.vue'
import KIcon from './KIcon.vue'
import type { Option } from './types'

defineOptions({ inheritAttrs: false })

const model = defineModel<string>({ default: '' })

const props = defineProps<{
  label: string
  options: (Option | string)[]
  help?: string
  error?: string
  disabled?: boolean
  labelHidden?: boolean
  id?: string
}>()

const autoId = useId()
const fieldId = computed(() => props.id ?? autoId)
const items = computed(() =>
  props.options.map((o) => (typeof o === 'string' ? { value: o, label: o } : o)),
)
</script>

<template>
  <KFieldShell
    :id="fieldId"
    v-slot="{ describedby, invalid }"
    :label="label"
    :help="help"
    :error="error"
    :label-hidden="labelHidden"
  >
    <div class="relative">
      <select
        :id="fieldId"
        v-model="model"
        v-bind="$attrs"
        :disabled="disabled"
        :aria-invalid="invalid ? 'true' : undefined"
        :aria-describedby="describedby"
        :class="[fieldClass({ invalid, disabled }), 'min-h-[46px] appearance-none pr-11 pl-4']"
      >
        <option v-for="item in items" :key="item.value" :value="item.value">
          {{ item.label }}
        </option>
      </select>
      <KIcon
        name="chevron-down"
        class="pointer-events-none absolute top-1/2 right-3.5 -translate-y-1/2 text-ink"
      />
    </div>
  </KFieldShell>
</template>
