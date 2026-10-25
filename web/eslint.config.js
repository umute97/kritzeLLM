import skipFormatting from '@vue/eslint-config-prettier/skip-formatting'
import { defineConfigWithVueTs, vueTsConfigs } from '@vue/eslint-config-typescript'
import { globalIgnores } from 'eslint/config'
import pluginVue from 'eslint-plugin-vue'

export default defineConfigWithVueTs(
  {
    name: 'app/files-to-lint',
    files: ['**/*.{ts,mts,vue}'],
  },
  globalIgnores(['**/dist/**', '**/coverage/**', 'src/api/schema.d.ts']),
  pluginVue.configs['flat/recommended'],
  vueTsConfigs.recommended,
  {
    // Optional TypeScript props are `undefined` already; a default adds nothing.
    rules: { 'vue/require-default-prop': 'off' },
  },
  skipFormatting,
)
