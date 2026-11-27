<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'

// What the chat helper is doing, one handwritten line beside the typing dots. Each new `text`
// flips in like the next card in a box, and stays up at least `hold` ms, so a burst of steps
// still flips through one by one.
const props = withDefaults(defineProps<{ text: string; hold?: number }>(), { hold: 900 })

const shown = ref(props.text)
const waiting: string[] = []
let timer: ReturnType<typeof setTimeout> | undefined

function flip() {
  timer = undefined
  const text = waiting.shift()
  if (text === undefined) return
  shown.value = text
  timer = setTimeout(flip, props.hold)
}

watch(
  () => props.text,
  (text) => {
    if (text === (waiting.at(-1) ?? shown.value)) return
    waiting.push(text)
    if (!timer) flip()
  },
)

onBeforeUnmount(() => clearTimeout(timer))
</script>

<template>
  <span aria-live="polite" class="block min-w-0 font-hand text-xl text-bark perspective-normal">
    <Transition
      mode="out-in"
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="opacity-0 motion-safe:-rotate-x-90"
      leave-active-class="transition duration-150 ease-in"
      leave-to-class="opacity-0 motion-safe:rotate-x-90"
    >
      <span :key="shown" class="block truncate">{{ shown }}</span>
    </Transition>
  </span>
</template>
