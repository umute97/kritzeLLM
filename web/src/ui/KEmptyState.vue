<script setup lang="ts">
// Say what's missing, then one way forward.
withDefaults(
  defineProps<{ title: string; text?: string; framed?: boolean; headingLevel?: 2 | 3 }>(),
  { text: undefined, framed: true, headingLevel: 2 },
)
</script>

<template>
  <div
    :class="[
      'flex flex-col items-center gap-2 px-5 py-7 text-center',
      framed && 'rounded-card border-[1.5px] border-dashed border-clay bg-cream',
    ]"
  >
    <slot name="illustration" />
    <component :is="`h${headingLevel}`" class="m-0 text-[22px]">{{ title }}</component>
    <p v-if="text || $slots.text" class="m-0 max-w-[420px] text-sm text-muted">
      <slot name="text">{{ text }}</slot>
    </p>
    <div v-if="$slots.default" class="mt-1.5 flex flex-wrap justify-center gap-2">
      <slot />
    </div>
  </div>
</template>
