<script setup lang="ts">
import type { Component } from 'vue'

import type { Crumb } from './types'

withDefaults(defineProps<{ items: Crumb[]; linkAs?: string | Component }>(), { linkAs: 'a' })
</script>

<template>
  <nav aria-label="Breadcrumb">
    <ol class="m-0 flex list-none flex-wrap items-center gap-1.5 p-0 text-sm">
      <li v-for="(item, index) in items" :key="index" class="flex items-center gap-1.5">
        <span v-if="index > 0" aria-hidden="true" class="font-hand text-lg text-bark">~</span>
        <component
          :is="linkAs"
          v-if="item.to && index < items.length - 1"
          :to="item.to"
          :href="typeof item.to === 'string' ? item.to : undefined"
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
