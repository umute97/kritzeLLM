<script setup lang="ts">
import { useSplitAttrs } from './attrs'

defineOptions({ inheritAttrs: false })

const model = defineModel<boolean>({ default: false })

defineProps<{ label: string; disabled?: boolean }>()

const { rootAttrs, controlAttrs } = useSplitAttrs()
</script>

<template>
  <label
    v-bind="rootAttrs()"
    :class="[
      'inline-flex min-h-11 items-center gap-2.5 font-semibold',
      disabled ? 'cursor-not-allowed text-muted' : 'cursor-pointer',
    ]"
  >
    <input
      v-bind="controlAttrs()"
      v-model="model"
      type="checkbox"
      :disabled="disabled"
      class="m-0 size-5.5 cursor-[inherit] accent-bark"
    />
    {{ label }}
  </label>
</template>
