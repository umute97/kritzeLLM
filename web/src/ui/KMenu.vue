<script setup lang="ts" generic="Id extends string">
import { computed, nextTick, onBeforeUnmount, ref, useId, useTemplateRef } from 'vue'

import KIcon from './KIcon.vue'
import KIconButton from './KIconButton.vue'
import type { MenuItem } from './types'

const props = withDefaults(
  defineProps<{ label: string; items: MenuItem<Id>[]; align?: 'start' | 'end' }>(),
  { align: 'end' },
)

const emit = defineEmits<{ select: [id: Id] }>()

const open = ref(false)
const root = useTemplateRef('root')
const menuId = useId()

// Spread on a custom `#trigger` too, so it's announced as a menu button and gets focus back.
const triggerProps = computed(() => ({
  'aria-haspopup': 'menu' as const,
  'aria-expanded': open.value,
  'aria-controls': open.value ? menuId : undefined,
}))

const itemClass =
  'flex min-h-[42px] cursor-pointer items-center gap-2.5 rounded-lg px-3 py-1.5 text-left focus:outline-none disabled:cursor-not-allowed disabled:text-muted disabled:hover:bg-transparent'

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

function choose(item: MenuItem<Id>) {
  hide()
  item.run?.()
  emit('select', item.id)
}

onBeforeUnmount(() => document.removeEventListener('pointerdown', onOutside))
</script>

<template>
  <div ref="root" class="relative inline-block">
    <slot
      name="trigger"
      :toggle="() => (open ? hide() : show())"
      :open="open"
      :trigger-props="triggerProps"
    >
      <KIconButton
        v-bind="triggerProps"
        icon="dots"
        :label="label"
        :class="open ? 'bg-accent!' : ''"
        @click="open ? hide() : show()"
      />
    </slot>
    <div
      v-if="open"
      :id="menuId"
      role="menu"
      :aria-label="label"
      :class="[
        'absolute z-40 mt-2 flex w-60 flex-col rounded-field border-[1.5px] border-ink bg-paper p-1.5 shadow-soft',
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
        :class="[itemClass, 'font-semibold text-ink hover:bg-accent/40 focus:bg-accent/40']"
        @click="choose(item)"
      >
        <KIcon v-if="item.icon" :name="item.icon" class="text-bark" />
        <span class="flex flex-col">
          <span class="flex flex-col">
            {{ item.label }}
            <span v-if="item.disabled && item.hint" class="text-xs font-normal">{{
              item.hint
            }}</span>
          </span>
          <span v-if="item.disabled && item.hint" class="text-xs font-normal">{{ item.hint }}</span>
        </span>
      </button>
      <template v-if="danger.length">
        <span v-if="safe.length" aria-hidden="true" class="mx-2 my-1.5 h-px bg-line" />
        <button
          v-for="item in danger"
          :key="item.id"
          type="button"
          role="menuitem"
          :disabled="item.disabled"
          :class="[itemClass, 'font-bold text-bark hover:bg-bark-soft focus:bg-bark-soft']"
          @click="choose(item)"
        >
          <KIcon v-if="item.icon" :name="item.icon" />
          <span class="flex flex-col">
            <span class="flex flex-col">
              {{ item.label }}
              <span v-if="item.disabled && item.hint" class="text-xs font-normal">{{
                item.hint
              }}</span>
            </span>
            <span v-if="item.disabled && item.hint" class="text-xs font-normal">{{
              item.hint
            }}</span>
          </span>
        </button>
      </template>
    </div>
  </div>
</template>
