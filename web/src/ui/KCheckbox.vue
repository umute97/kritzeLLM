<script setup lang="ts">
const model = defineModel<boolean>({ default: false })

defineProps<{ label: string; disabled?: boolean }>()
</script>

<template>
  <label
    :class="[
      'inline-flex min-h-11 items-center gap-2.5 font-semibold',
      disabled ? 'cursor-not-allowed text-muted' : 'cursor-pointer',
    ]"
  >
    <input
      v-model="model"
      type="checkbox"
      :disabled="disabled"
      class="m-0 size-5.5 cursor-[inherit] accent-bark"
    />
    {{ label }}
  </label>
</template>
