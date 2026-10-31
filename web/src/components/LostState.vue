<script setup lang="ts">
import { useI18n } from 'vue-i18n'

import { KButton, KEmptyState } from '@/ui'

// Somewhere that isn't there (any more), with the way home.
defineProps<{ title: string; text: string }>()

const { t } = useI18n()
</script>

<template>
  <KEmptyState :title="title" :text="text" doodle="squiggle">
    <KButton to="/">{{ t('lost.back') }}</KButton>
  </KEmptyState>
</template>
