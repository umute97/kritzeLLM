<script setup lang="ts">
// A chat message. Answers come as a bubble or as a letter on lined paper; `streaming` adds a
// caret at the end, and `error` turns it into a "the answer stopped" note with room for a retry.
withDefaults(
  defineProps<{
    role: 'user' | 'assistant'
    variant?: 'bubble' | 'letter'
    streaming?: boolean
    error?: boolean
  }>(),
  { variant: 'bubble' },
)
</script>

<template>
  <div
    v-if="role === 'user'"
    class="max-w-[78%] self-end rounded-[18px_18px_6px_18px] border-[1.5px] border-ink bg-accent/40 px-4.5 py-3"
  >
    <slot />
  </div>
  <div v-else class="flex max-w-[90%] items-start gap-3" :role="error ? 'alert' : undefined">
    <span
      aria-hidden="true"
      :class="[
        'flex size-9 shrink-0 items-center justify-center rounded-full border-[1.5px] border-ink',
        error ? 'bg-bark text-cream' : 'bg-lemon',
      ]"
    >
      <svg v-if="error" width="16" height="16" viewBox="0 0 24 24" fill="none">
        <path
          d="M12 6.5v7M12 17.5h.01"
          stroke="currentColor"
          stroke-width="3"
          stroke-linecap="round"
        />
      </svg>
      <svg v-else width="20" height="20" viewBox="0 0 32 32" fill="none">
        <path
          d="M16 4 L18.5 13.5 L28 16 L18.5 18.5 L16 28 L13.5 18.5 L4 16 L13.5 13.5 Z"
          fill="#fffdf8"
          stroke="#3d2b22"
          stroke-width="1.5"
          stroke-linejoin="round"
        />
      </svg>
    </span>
    <div
      :aria-live="streaming ? 'polite' : undefined"
      :class="[
        'flex flex-col gap-2 rounded-[6px_18px_18px_18px]',
        error
          ? 'border-2 border-bark bg-bark-soft px-4.5 py-3'
          : variant === 'letter'
            ? 'paper-lines border border-line px-5.5 pt-1 pb-2 font-hand text-[19px] leading-8 [--line:32px]'
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
    </div>
  </div>
</template>
