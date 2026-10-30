<script setup lang="ts">
import { computed } from 'vue'

// A bar when we know how long. Use KSpinner when we don't.
const props = withDefaults(
  defineProps<{
    value: number
    max?: number
    label: string
    size?: 'lg' | 'md' | 'sm'
    meter?: boolean
    color?: 'accent' | 'lemon' | 'orchid'
  }>(),
  { max: 100, size: 'md', color: 'accent' },
)

const percent = computed(() =>
  props.max > 0 ? Math.min(100, Math.max(0, (props.value / props.max) * 100)) : 0,
)
const fills = { accent: 'bg-accent', lemon: 'bg-lemon', orchid: 'bg-orchid' }
</script>

<template>
  <div
    :role="meter ? 'meter' : 'progressbar'"
    :aria-valuemin="0"
    :aria-valuemax="max"
    :aria-valuenow="value"
    :aria-label="label"
    :class="[
      'overflow-hidden rounded-full border-[1.5px] border-ink bg-paper',
      { lg: 'h-4', md: 'h-3.5', sm: 'h-2.5' }[size],
    ]"
  >
    <div
      :class="[
        'h-full transition-[width] duration-300',
        fills[color],
        percent > 0 && percent < 100 && size !== 'sm' && 'border-r-[1.5px] border-ink',
      ]"
      :style="{ width: `${percent}%` }"
    />
  </div>
</template>
