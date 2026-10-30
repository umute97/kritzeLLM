<script setup lang="ts">
import { computed, ref, useId } from 'vue'

import { joinIds, useSplitAttrs } from './attrs'
import KFieldShell from './KFieldShell.vue'
import KIconButton from './KIconButton.vue'
import { fieldClass } from './styles'

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
      <input
        :id="fieldId"
        v-model="model"
        v-bind="controlAttrs()"
        :type="inputType"
        :disabled="disabled"
        :placeholder="placeholder"
        :aria-invalid="invalid ? 'true' : undefined"
        :aria-describedby="joinIds(describedby, $attrs['aria-describedby'])"
        :class="[fieldClass({ invalid, disabled }), 'min-h-[46px] px-4', revealable && 'pr-12']"
      />
      <KIconButton
        v-if="revealable"
        :icon="revealed ? 'eye-off' : 'eye'"
        :label="revealed ? `Hide ${label}` : `Show ${label}`"
        variant="quiet"
        :pressed="revealed"
        class="absolute top-1/2 right-0.5 -translate-y-1/2"
        @click="revealed = !revealed"
      />
    </div>
  </KFieldShell>
</template>
