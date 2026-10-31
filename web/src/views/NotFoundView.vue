<script setup lang="ts">
import { useI18n } from 'vue-i18n'

import LostState from '@/components/LostState.vue'
import { KPage } from '@/ui'

const { t } = useI18n()
</script>

<template>
  <KPage width="narrow">
    <LostState :title="t('lost.notFoundTitle')" :text="t('lost.notFound')" />
  </KPage>
</template>
