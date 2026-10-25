<script setup lang="ts">
// Say what's missing, then one way forward.
withDefaults(defineProps<{ title: string; text?: string; framed?: boolean }>(), {
  text: undefined,
  framed: true,
})
</script>

<template>
  <div
    :class="[
      'flex flex-col items-center gap-2 px-5 py-7 text-center',
      framed && 'rounded-card border-[1.5px] border-dashed border-clay bg-cream',
    ]"
  >
    <slot name="illustration" />
    <h2 class="m-0 text-[22px]">{{ title }}</h2>
    <p v-if="text" class="m-0 max-w-[420px] text-sm text-muted">{{ text }}</p>
    <div v-if="$slots.default" class="mt-1.5 flex flex-wrap justify-center gap-2">
      <slot />
    </div>
  </div>
</template>
