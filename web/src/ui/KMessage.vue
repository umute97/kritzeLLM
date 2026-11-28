<script setup lang="ts">
import KIcon from './KIcon.vue'
import KIconBadge from './KIconBadge.vue'
import KTypingDots from './KTypingDots.vue'

// A chat message. `streaming` adds a caret at the end of an answer, and `error` turns it into a
// "the answer stopped" note with room for a retry. `typing` is an answer that hasn't started yet:
// dots, and the slot beside them. A `footer` sits under a dashed line at the bottom of the bubble.
defineProps<{
  author: 'user' | 'assistant'
  streaming?: boolean
  error?: boolean
  typing?: boolean
}>()
</script>

<template>
  <div
    v-if="author === 'user'"
    class="flex max-w-[78%] flex-col gap-2 self-end rounded-[18px_18px_6px_18px] border-[1.5px] border-ink bg-accent/40 px-4.5 py-3"
  >
    <div><slot /></div>
    <div v-if="$slots.actions" class="flex flex-wrap gap-2">
      <slot name="actions" />
    </div>
  </div>
  <div
    v-else
    :class="['flex max-w-[90%] gap-3', typing ? 'items-center' : 'items-start']"
    :role="error ? 'alert' : undefined"
  >
    <KIconBadge :class="error ? 'bg-bark text-cream' : 'bg-lemon'">
      <KIcon v-if="error" name="alert" :size="16" />
      <svg v-else width="20" height="20" viewBox="0 0 32 32" fill="none">
        <path
          d="M16 4 L18.5 13.5 L28 16 L18.5 18.5 L16 28 L13.5 18.5 L4 16 L13.5 13.5 Z"
          class="fill-paper stroke-ink"
          stroke-width="1.5"
          stroke-linejoin="round"
        />
      </svg>
    </KIconBadge>
    <div v-if="typing" class="flex min-w-0 items-center gap-3 font-hand text-xl text-bark">
      <KTypingDots class="shrink-0" />
      <slot />
    </div>
    <div
      v-else
      :aria-live="streaming ? 'polite' : undefined"
      :class="[
        'flex flex-col gap-2 rounded-[6px_18px_18px_18px]',
        error
          ? 'border-2 border-bark bg-bark-soft px-4.5 py-3'
          : 'border-[1.5px] border-ink bg-paper px-4.5 py-3 leading-[1.7]',
      ]"
    >
      <div>
        <slot /><span
          v-if="streaming"
          aria-hidden="true"
          class="ml-0.5 inline-block h-[18px] w-[9px] animate-blink rounded-sm border border-ink bg-accent align-[-3px]"
        />
      </div>
      <div v-if="$slots.actions" class="flex flex-wrap gap-2">
        <slot name="actions" />
      </div>
      <div v-if="$slots.footer" class="-mb-1.5 border-t-[1.5px] border-dashed border-line pt-1">
        <slot name="footer" />
      </div>
    </div>
  </div>
</template>
