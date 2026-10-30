import './styles/main.css'

import { createPinia } from 'pinia'
import { createApp } from 'vue'
import { RouterLink } from 'vue-router'

import App from './App.vue'
import { router } from './router'
import { createCottage } from './ui'

createApp(App)
  .use(createPinia())
  .use(router)
  .use(createCottage({ link: RouterLink }))
  .mount('#app')
