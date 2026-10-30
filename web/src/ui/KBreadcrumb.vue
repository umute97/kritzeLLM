<script setup lang="ts">
import { useLinkComponent } from './plugin'
import { linkAttrs } from './polymorphic'
import type { Crumb } from './types'
import { useUiMessages } from './messages'

defineProps<{ items: Crumb[] }>()

const link = useLinkComponent()

const ui = useUiMessages()
</script>

<template>
  <nav :aria-label="ui.breadcrumb">
    <ol class="m-0 flex list-none flex-wrap items-center gap-1.5 p-0 text-sm">
      <li v-for="(item, index) in items" :key="index" class="flex items-center gap-1.5">
        <span v-if="index > 0" aria-hidden="true" class="font-hand text-lg text-bark">~</span>
        <component
          :is="link"
          v-if="item.to && index < items.length - 1"
          v-bind="linkAttrs(link, item.to)"
          class="font-bold"
          >{{ item.label }}</component
        >
        <span
          v-else
          :aria-current="index === items.length - 1 ? 'page' : undefined"
          class="font-semibold"
          >{{ item.label }}</span
        >
      </li>
    </ol>
  </nav>
</template>
