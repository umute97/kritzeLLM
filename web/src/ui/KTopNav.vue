<script setup lang="ts">
import { ref, useId } from 'vue'

import KIconButton from './KIconButton.vue'
import { useUiMessages } from './messages'

// Brand, links (KNavLink) and a little greeting. On phones the links fold behind a menu button.
defineProps<{ label?: string }>()

const open = ref(false)
const linksId = useId()

const ui = useUiMessages()
</script>

<template>
  <nav :aria-label="label ?? ui.mainNav" class="border-b-[1.5px] border-ink bg-cream">
    <div
      class="mx-auto flex max-w-[1200px] flex-wrap items-center gap-x-7 gap-y-2 px-4 py-3 sm:px-6"
    >
      <div class="flex flex-1 items-center justify-between gap-3 sm:flex-none">
        <slot name="brand" />
        <KIconButton
          icon="menu"
          :label="ui.menu"
          :aria-expanded="open"
          :aria-controls="linksId"
          :class="['sm:hidden', open && 'bg-accent!']"
          @click="open = !open"
        />
      </div>
      <div
        :id="linksId"
        :class="[
          'w-full flex-col gap-1 sm:flex sm:w-auto sm:flex-1 sm:flex-row sm:flex-wrap',
          open ? 'flex' : 'hidden',
        ]"
        @click="open = false"
      >
        <slot />
      </div>
      <div v-if="$slots.end" class="hidden sm:block">
        <slot name="end" />
      </div>
    </div>
  </nav>
</template>
