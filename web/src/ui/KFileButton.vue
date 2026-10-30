<script setup lang="ts">
import { useSplitAttrs } from './attrs'
import type { IconName } from './icons'
import KButton from './KButton.vue'

defineOptions({ inheritAttrs: false })

withDefaults(
  defineProps<{
    accept?: string
    multiple?: boolean
    disabled?: boolean
    variant?: 'main' | 'second' | 'quiet'
    size?: 'md' | 'sm'
    icon?: IconName
  }>(),
  {
    accept: 'image/jpeg,image/png,image/heic,image/heif,image/webp,.heic,.heif',
    multiple: true,
    variant: 'main',
    size: 'md',
    icon: 'upload',
  },
)

const { rootAttrs, controlAttrs } = useSplitAttrs()

const emit = defineEmits<{ files: [files: File[]] }>()

function onPick(event: Event) {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files ?? [])
  input.value = ''
  if (files.length) emit('files', files)
}
</script>

<template>
  <KButton
    v-bind="rootAttrs()"
    as="label"
    :variant="variant"
    :size="size"
    :icon="icon"
    :disabled="disabled"
    class="relative"
  >
    <slot />
    <input
      v-bind="controlAttrs()"
      type="file"
      class="sr-only"
      :accept="accept"
      :multiple="multiple"
      :disabled="disabled"
      @change="onPick"
    />
  </KButton>
</template>
