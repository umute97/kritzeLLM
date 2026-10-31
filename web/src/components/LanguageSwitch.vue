<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import { currentLocale, setLocale, type Locale } from '@/i18n'
import { KSegmented } from '@/ui'

// Each language is named in its own words, so it's findable whichever one is on screen.
const options: { value: Locale; label: string }[] = [
  { value: 'en', label: 'English' },
  { value: 'de', label: 'Deutsch' },
]

const { t } = useI18n()
const locale = computed({ get: currentLocale, set: setLocale })
</script>

<template>
  <KSegmented v-model="locale" :label="t('language.label')" :options="options" size="sm" />
</template>
