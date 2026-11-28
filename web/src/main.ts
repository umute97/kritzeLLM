import './styles/main.css'

import { createPinia } from 'pinia'
import { createApp } from 'vue'
import { RouterLink } from 'vue-router'

import { configureApi } from './api/client'
import App from './App.vue'
import { currentLocale, i18n, uiMessages } from './i18n'
import { router } from './router'
import { useAuth } from './stores/auth'
import { useHealth } from './stores/health'
import { createCottage } from './ui'

document.documentElement.lang = currentLocale()

const pinia = createPinia()
const app = createApp(App)
  .use(pinia)
  .use(router)
  .use(i18n)
  .use(createCottage({ link: RouterLink, messages: uiMessages }))

const auth = useAuth(pinia)
const health = useHealth(pinia)
configureApi({
  token: () => auth.token,
  onUnauthorized: auth.reject,
  onOffline: health.markOffline,
})

app.mount('#app')
