<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, useTemplateRef } from 'vue'

import KIcon from './KIcon.vue'
import KIconButton from './KIconButton.vue'
import type { MenuItem } from './types'

const props = withDefaults(
  defineProps<{ label: string; items: MenuItem[]; align?: 'start' | 'end' }>(),
  { align: 'end' },
)

const emit = defineEmits<{ select: [id: string] }>()

const open = ref(false)
const root = useTemplateRef('root')
const trigger = useTemplateRef<InstanceType<typeof KIconButton>>('trigger')

const safe = computed(() => props.items.filter((item) => !item.danger))
const danger = computed(() => props.items.filter((item) => item.danger))

function menuItems(): HTMLButtonElement[] {
  return Array.from(root.value?.querySelectorAll<HTMLButtonElement>('[role="menuitem"]') ?? [])
}

async function show() {
  open.value = true
  document.addEventListener('pointerdown', onOutside)
  await nextTick()
  menuItems()
    .find((el) => !el.disabled)
    ?.focus()
}

function hide(refocus = true) {
  open.value = false
  document.removeEventListener('pointerdown', onOutside)
  if (refocus) (trigger.value?.$el as HTMLElement | undefined)?.focus()
}

function onOutside(event: PointerEvent) {
  if (!root.value?.contains(event.target as Node)) hide(false)
}

function onKeydown(event: KeyboardEvent) {
  const items = menuItems().filter((el) => !el.disabled)
  const at = items.indexOf(document.activeElement as HTMLButtonElement)
  if (event.key === 'Escape') {
    event.preventDefault()
    hide()
  } else if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
    event.preventDefault()
    const step = event.key === 'ArrowDown' ? 1 : -1
    items[(at + step + items.length) % items.length]?.focus()
  } else if (event.key === 'Tab') {
    hide(false)
  }
}

function choose(item: MenuItem) {
  hide()
  emit('select', item.id)
}

onBeforeUnmount(() => document.removeEventListener('pointerdown', onOutside))
</script>

<template>
  <div ref="root" class="relative inline-block">
    <slot name="trigger" :toggle="() => (open ? hide() : show())" :open="open">
      <KIconButton
        ref="trigger"
        icon="dots"
        :label="label"
        aria-haspopup="menu"
        :aria-expanded="open"
        :class="open ? 'bg-accent!' : ''"
        @click="open ? hide() : show()"
      />
    </slot>
    <div
      v-if="open"
      role="menu"
      :aria-label="label"
      :class="[
        'absolute z-40 mt-2 flex w-60 flex-col rounded-field border-[1.5px] border-ink bg-paper p-1.5 shadow-[0_6px_0_rgb(61_43_34/0.2)]',
        align === 'end' ? 'right-0' : 'left-0',
      ]"
      @keydown="onKeydown"
    >
      <button
        v-for="item in safe"
        :key="item.id"
        type="button"
        role="menuitem"
        :disabled="item.disabled"
        class="flex min-h-[42px] cursor-pointer items-center gap-2.5 rounded-lg px-3 text-left font-semibold text-ink hover:bg-accent/40 focus:bg-accent/40 focus:outline-none disabled:cursor-not-allowed disabled:text-muted"
        @click="choose(item)"
      >
        <KIcon v-if="item.icon" :name="item.icon" class="text-bark" />
        {{ item.label }}
      </button>
      <template v-if="danger.length">
        <span v-if="safe.length" aria-hidden="true" class="mx-2 my-1.5 h-px bg-line" />
        <button
          v-for="item in danger"
          :key="item.id"
          type="button"
          role="menuitem"
          :disabled="item.disabled"
          class="flex min-h-[42px] cursor-pointer items-center gap-2.5 rounded-lg px-3 text-left font-bold text-bark hover:bg-bark-soft focus:bg-bark-soft focus:outline-none disabled:cursor-not-allowed disabled:text-muted disabled:hover:bg-transparent"
          @click="choose(item)"
        >
          <KIcon v-if="item.icon" :name="item.icon" />
          {{ item.label }}
        </button>
      </template>
    </div>
  </div>
</template>
