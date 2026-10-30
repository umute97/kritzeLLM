<script setup lang="ts" generic="T extends string = string">
import { computed, useId } from 'vue'

import { joinIds, useSplitAttrs } from './attrs'
import KFieldShell from './KFieldShell.vue'
import KIcon from './KIcon.vue'
import { fieldClass } from './styles'
import type { Option } from './types'

defineOptions({ inheritAttrs: false })

const model = defineModel<T>()

const props = defineProps<{
  label: string
  options: (Option<T> | T)[]
  help?: string
  error?: string
  disabled?: boolean
  optional?: boolean
  labelHidden?: boolean
  id?: string
}>()

const autoId = useId()
const fieldId = computed(() => props.id ?? autoId)
const items = computed(() =>
  props.options.map((o) => (typeof o === 'string' ? { value: o, label: o } : o)),
)
const { rootAttrs, controlAttrs } = useSplitAttrs()
</script>

<template>
  <KFieldShell
    v-bind="rootAttrs()"
    :id="fieldId"
    v-slot="{ describedby, invalid }"
    :label="label"
    :help="help"
    :error="error"
    :optional="optional"
    :label-hidden="labelHidden"
  >
    <div class="relative">
      <select
        :id="fieldId"
        v-model="model"
        v-bind="controlAttrs()"
        :disabled="disabled"
        :aria-invalid="invalid ? 'true' : undefined"
        :aria-describedby="joinIds(describedby, $attrs['aria-describedby'])"
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
