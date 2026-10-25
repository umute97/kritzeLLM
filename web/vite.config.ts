import { fileURLToPath, URL } from 'node:url'

import tailwindcss from '@tailwindcss/vite'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  server: {
    // `just web-dev` talks to the API from `just backend-dev` or the compose stack.
    proxy: { '/api': `http://localhost:${process.env.API_PORT || 8000}` },
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  test: {
    environment: 'jsdom',
    include: ['src/**/__tests__/*.spec.ts'],
    setupFiles: ['src/test-setup.ts'],
  },
})
