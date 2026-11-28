<script setup lang="ts">
import KButton from './KButton.vue'
import KIcon from './KIcon.vue'

// Shows and hides a part of the page: point `controls` at that part's id. A `chevron` toggle
// turns its arrow; a `quiet` one is a small underlined button whose words say what it does.
const open = defineModel<boolean>('open', { default: false })

withDefaults(
  defineProps<{ controls?: string; variant?: 'chevron' | 'quiet'; size?: 'sm' | 'md' }>(),
  { variant: 'chevron', size: 'sm' },
)
</script>

<template>
  <KButton
    v-if="variant === 'quiet'"
    variant="quiet"
    size="sm"
    :aria-expanded="open"
    :aria-controls="controls"
    @click="open = !open"
  >
    <slot />
  </KButton>
  <button
    v-else
    type="button"
    :aria-expanded="open"
    :aria-controls="controls"
    class="inline-flex cursor-pointer items-center gap-1.5"
    @click="open = !open"
  >
    <slot />
    <KIcon name="chevron-down" :size="size === 'sm' ? 13 : 16" :class="open && 'rotate-180'" />
  </button>
</template>
