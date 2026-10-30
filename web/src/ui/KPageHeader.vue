<script setup lang="ts">
// The top of a screen, with its one h1.
withDefaults(defineProps<{ title: string; subtitle?: string; meta?: string }>(), {
  subtitle: undefined,
  meta: undefined,
})
</script>

<template>
  <header class="flex flex-wrap items-end justify-between gap-4">
    <div class="flex min-w-0 flex-col gap-1">
      <slot name="eyebrow" />
      <div class="flex flex-wrap items-center gap-3.5">
        <h1 class="m-0 text-[40px] leading-tight sm:text-5xl">{{ title }}</h1>
        <slot name="title-after" />
      </div>
      <span v-if="subtitle" class="font-hand text-[19px] text-bark">{{ subtitle }}</span>
      <span v-if="meta" class="text-sm text-muted">{{ meta }}</span>
    </div>
    <div v-if="$slots.actions" class="flex flex-wrap items-center gap-2.5">
      <slot name="actions" />
    </div>
  </header>
</template>
