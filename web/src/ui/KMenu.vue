<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, useId, useTemplateRef } from 'vue'

import KIcon from './KIcon.vue'
import KIconButton from './KIconButton.vue'
import type { MenuItem } from './types'

const props = defineProps<{ label: string; items: MenuItem[] }>()

const open = ref(false)
const root = useTemplateRef('root')
const menuId = useId()

const itemClass =
  'flex min-h-[42px] cursor-pointer items-center gap-2.5 rounded-lg px-3 py-1.5 text-left focus:outline-none disabled:cursor-not-allowed disabled:text-muted disabled:hover:bg-transparent'

const groups = computed(() =>
  [
    {
      items: props.items.filter((item) => !item.danger),
      look: 'font-semibold text-ink hover:bg-accent/40 focus:bg-accent/40',
      icon: 'text-bark',
    },
    {
      items: props.items.filter((item) => item.danger),
      look: 'font-bold text-bark hover:bg-bark-soft focus:bg-bark-soft',
      icon: '',
    },
  ].filter((group) => group.items.length > 0),
)

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
  if (refocus) root.value?.querySelector<HTMLElement>('[aria-haspopup="menu"]')?.focus()
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
  item.run?.()
}

onBeforeUnmount(() => document.removeEventListener('pointerdown', onOutside))
</script>

<template>
  <div ref="root" class="relative inline-block">
    <KIconButton
      icon="dots"
      :label="label"
      aria-haspopup="menu"
      :aria-expanded="open"
      :aria-controls="open ? menuId : undefined"
      :class="open ? 'bg-accent!' : ''"
      @click="open ? hide() : show()"
    />
    <div
      v-if="open"
      :id="menuId"
      role="menu"
      :aria-label="label"
      class="absolute right-0 z-40 mt-2 flex w-60 flex-col rounded-field border-[1.5px] border-ink bg-paper p-1.5 shadow-soft"
      @keydown="onKeydown"
    >
      <template v-for="(group, at) in groups" :key="at">
        <span v-if="at > 0" aria-hidden="true" class="mx-2 my-1.5 h-px bg-line" />
        <button
          v-for="item in group.items"
          :key="item.id"
          type="button"
          role="menuitem"
          :disabled="item.disabled"
          :class="[itemClass, group.look]"
          @click="choose(item)"
        >
          <KIcon v-if="item.icon" :name="item.icon" :class="group.icon" />
          <span class="flex flex-col">
            {{ item.label }}
            <span v-if="item.disabled && item.hint" class="text-xs font-normal">{{
              item.hint
            }}</span>
          </span>
        </button>
      </template>
    </div>
  </div>
</template>
