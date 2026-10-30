<script setup lang="ts">
import { computed } from 'vue'

import KToast from './KToast.vue'
import { useToasts } from './toasts'

// Bottom right on wide screens, top and full width on phones. Three at most; older ones fold away.
const { items, dismiss, pause, resume } = useToasts()

const visible = computed(() => items.value.slice(-3))
</script>

<template>
  <div
    role="region"
    aria-label="Notifications"
    class="pointer-events-none fixed inset-x-4 top-4 z-50 flex flex-col gap-3.5 sm:inset-x-auto sm:top-auto sm:right-6 sm:bottom-6 sm:w-[440px]"
  >
    <KToast
      v-for="toast in visible"
      :key="toast.id"
      class="pointer-events-auto"
      :tone="toast.tone"
      :title="toast.title"
      :detail="toast.detail"
      :technical="toast.technical"
      :icon="toast.icon"
      :action-label="toast.action?.label"
      :progress="toast.progress"
      @mouseenter="pause(toast.id)"
      @mouseleave="resume(toast.id)"
      @focusin="pause(toast.id)"
      @focusout="resume(toast.id)"
      @dismiss="dismiss(toast.id)"
      @action="toast.action?.run()"
    />
  </div>
</template>
