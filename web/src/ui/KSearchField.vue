<script setup lang="ts">
import { computed, useId, useTemplateRef } from 'vue'

import { joinIds, useSplitAttrs } from './attrs'
import KFieldShell from './KFieldShell.vue'
import KIcon from './KIcon.vue'
import KIconButton from './KIconButton.vue'
import { focusWithinRing } from './styles'
import { useUiMessages } from './messages'

// Round like the buttons, and a search form of its own: Enter or a submit button in the
// trailing slot searches. So don't put it inside another form.
defineOptions({ inheritAttrs: false })

const model = defineModel<string>({ default: '' })

const props = withDefaults(
  defineProps<{ label: string; placeholder?: string; size?: 'md' | 'lg'; id?: string }>(),
  { placeholder: undefined, size: 'md', id: undefined },
)

const emit = defineEmits<{ search: [query: string] }>()

const autoId = useId()
const fieldId = computed(() => props.id ?? autoId)
const input = useTemplateRef('input')
const { rootAttrs, controlAttrs } = useSplitAttrs()

function clear() {
  model.value = ''
  input.value?.focus()
}

const ui = useUiMessages()
</script>

<template>
  <form v-bind="rootAttrs()" role="search" @submit.prevent="emit('search', model)">
    <KFieldShell :id="fieldId" v-slot="{ describedby }" :label="label" label-hidden>
      <div
        :class="[
          'flex items-center gap-1 rounded-full border-ink bg-paper pl-4',
          focusWithinRing,
          size === 'lg' ? 'min-h-14 border-2 pl-5 shadow-soft' : 'min-h-[46px] border-[1.5px]',
        ]"
      >
        <KIcon name="search" :size="size === 'lg' ? 22 : 18" class="text-ink" />
        <input
          :id="fieldId"
          ref="input"
          v-model="model"
          v-bind="controlAttrs()"
          type="search"
          :placeholder="placeholder"
          :aria-describedby="joinIds(describedby, $attrs['aria-describedby'])"
          :class="[
            'min-w-0 flex-1 bg-transparent px-2 text-ink placeholder:text-hint focus:outline-none [&::-webkit-search-cancel-button]:hidden',
            size === 'lg' ? 'h-13 text-lg' : 'h-11 text-base',
          ]"
        />
        <KIconButton
          v-if="model"
          icon="close"
          :label="ui.clearSearch"
          variant="quiet"
          @click="clear"
        />
        <div v-if="$slots.default" class="pr-1.5">
          <slot />
        </div>
      </div>
    </KFieldShell>
  </form>
</template>
