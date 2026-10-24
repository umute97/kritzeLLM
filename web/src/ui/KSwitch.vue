<script setup lang="ts">
import { useId } from 'vue'

const model = defineModel<boolean>({ default: false })

defineProps<{ label: string; disabled?: boolean }>()

const labelId = useId()
</script>

<template>
  <div class="inline-flex min-h-11 items-center gap-2.5">
    <button
      type="button"
      role="switch"
      :aria-checked="model"
      :aria-labelledby="labelId"
      :disabled="disabled"
      :class="[
        'relative h-8 w-14 shrink-0 rounded-full border-[1.5px] border-ink transition-colors',
        model ? 'bg-accent' : 'bg-mute',
        disabled ? 'cursor-not-allowed opacity-60' : 'cursor-pointer',
      ]"
      @click="model = !model"
    >
      <span
        :class="[
          'absolute top-[3px] size-[23px] rounded-full border-[1.5px] border-ink bg-paper transition-[left] duration-150',
          model ? 'left-[27px]' : 'left-[3px]',
        ]"
      />
    </button>
    <span :id="labelId" class="font-semibold">{{ label }}</span>
  </div>
</template>
