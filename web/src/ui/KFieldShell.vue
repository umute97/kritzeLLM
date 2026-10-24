<script setup lang="ts">
import { computed } from 'vue'

import KIcon from './KIcon.vue'

// A label above, help or an error below, never just a placeholder.
const props = defineProps<{
  id: string
  label: string
  help?: string
  error?: string
  optional?: boolean
  labelHidden?: boolean
}>()

const describedby = computed(() =>
  props.error ? `${props.id}-error` : props.help ? `${props.id}-help` : undefined,
)
</script>

<template>
  <div class="flex flex-col gap-1.5">
    <label :for="id" :class="labelHidden ? 'sr-only' : 'text-sm font-bold'">
      {{ label }}
      <span v-if="optional" class="font-normal text-muted">(optional)</span>
    </label>
    <slot :describedby="describedby" :invalid="!!error" />
    <p
      v-if="error"
      :id="`${id}-error`"
      class="flex items-center gap-1.5 text-sm font-bold text-bark"
    >
      <KIcon name="alert-circle" :size="16" />
      {{ error }}
    </p>
    <p v-else-if="help" :id="`${id}-help`" class="text-[13px] text-muted">{{ help }}</p>
  </div>
</template>
