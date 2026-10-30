<script setup lang="ts">
import KSpinner from './KSpinner.vue'

// A photo, or lined paper until there is one: with the default slot written on it (an excerpt),
// or a daisy while `loadingLabel` says it's coming. Frame it with classes; set `--line` there too.
withDefaults(
  defineProps<{
    src?: string
    alt?: string
    width?: number
    height?: number
    fit?: 'contain' | 'cover'
    lazy?: boolean
    dimmed?: boolean
    loadingLabel?: string
  }>(),
  {
    src: undefined,
    alt: '',
    width: undefined,
    height: undefined,
    fit: 'cover',
    loadingLabel: undefined,
  },
)
</script>

<template>
  <span
    class="relative block overflow-hidden"
    :style="width && height ? { aspectRatio: `${width} / ${height}` } : undefined"
  >
    <img
      v-if="src"
      :src="src"
      :alt="alt"
      :loading="lazy ? 'lazy' : undefined"
      :class="[
        'size-full',
        fit === 'cover' ? 'object-cover' : 'object-contain',
        dimmed && 'opacity-35',
      ]"
    />
    <span
      v-else
      :class="['paper-lines flex size-full items-center justify-center', dimmed && 'opacity-35']"
    >
      <KSpinner v-if="loadingLabel" variant="daisy" :size="48" :label="loadingLabel" />
      <span v-else-if="$slots.default" class="size-full self-start"><slot /></span>
    </span>
    <slot name="overlay" />
  </span>
</template>
