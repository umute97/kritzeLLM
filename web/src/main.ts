import './styles/main.css'

import { createPinia } from 'pinia'
import { createApp } from 'vue'
import { RouterLink } from 'vue-router'

import App from './App.vue'
import { currentLocale, i18n, uiMessages } from './i18n'
import { router } from './router'
import { createCottage } from './ui'

document.documentElement.lang = currentLocale()

createApp(App)
  .use(createPinia())
  .use(router)
  .use(i18n)
  .use(createCottage({ link: RouterLink, messages: uiMessages }))
  .mount('#app')
