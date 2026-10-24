<script setup lang="ts">
import KIcon from './KIcon.vue'
import KSpinner from './KSpinner.vue'

// What the chat helper is doing: a handwritten line while it works, folded up once it's done.
withDefaults(
  defineProps<{
    state: 'working' | 'done'
    icon?: 'search' | 'book'
    /** Done lines can unfold the steps; leave undefined for a plain line. */
    expanded?: boolean
  }>(),
  { icon: 'search', expanded: undefined },
)

const emit = defineEmits<{ toggle: [] }>()
</script>

<template>
  <button
    v-if="state === 'done' && expanded !== undefined"
    type="button"
    :aria-expanded="expanded"
    class="flex cursor-pointer items-center gap-2 self-start py-1 font-hand text-xl text-bark"
    @click="emit('toggle')"
  >
    <KIcon name="check" />
    <slot />
    <KIcon name="chevron-down" :size="14" :class="expanded && 'rotate-180'" />
  </button>
  <div v-else class="flex items-center gap-2 font-hand text-xl text-bark">
    <KSpinner v-if="state === 'working' && icon === 'search'" />
    <KIcon v-else :name="state === 'done' ? 'check' : icon" />
    <slot />
  </div>
</template>
