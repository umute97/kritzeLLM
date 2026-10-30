<script setup lang="ts">
import { computed, ref, useId } from 'vue'

import { joinIds } from './attrs'
import { fieldClass } from './field'
import KFieldShell from './KFieldShell.vue'
import KIcon from './KIcon.vue'

defineOptions({ inheritAttrs: false })

const model = defineModel<string | number>({ default: '' })

const props = withDefaults(
  defineProps<{
    label: string
    type?: 'text' | 'password' | 'email' | 'number' | 'url'
    help?: string
    error?: string
    disabled?: boolean
    placeholder?: string
    optional?: boolean
    labelHidden?: boolean
    /** A password field with an eye button to peek. */
    revealable?: boolean
    id?: string
  }>(),
  { type: 'text' },
)

const autoId = useId()
const fieldId = computed(() => props.id ?? autoId)
const revealed = ref(false)
const inputType = computed(() =>
  props.type === 'password' && revealed.value ? 'text' : props.type,
)
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
    <div class="relative">
      <input
        :id="fieldId"
        v-model="model"
        v-bind="$attrs"
        :type="inputType"
        :disabled="disabled"
        :placeholder="placeholder"
        :aria-invalid="invalid ? 'true' : undefined"
        :aria-describedby="joinIds(describedby, $attrs['aria-describedby'])"
        :class="[fieldClass({ invalid, disabled }), 'min-h-[46px] px-4', revealable && 'pr-12']"
      />
      <button
        v-if="revealable"
        type="button"
        class="absolute top-1/2 right-0.5 flex size-11 -translate-y-1/2 cursor-pointer items-center justify-center rounded-full text-ink"
        :aria-label="revealed ? `Hide ${label}` : `Show ${label}`"
        :aria-pressed="revealed"
        @click="revealed = !revealed"
      >
        <KIcon :name="revealed ? 'eye-off' : 'eye'" :size="20" />
      </button>
    </div>
  </KFieldShell>
</template>
