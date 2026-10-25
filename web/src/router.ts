import { createRouter, createWebHistory } from 'vue-router'

import LibraryView from '@/views/LibraryView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'library', component: LibraryView },
    { path: '/journals/:journalId', name: 'journal', component: LibraryView, props: true },
    {
      path: '/pages/:pageId',
      name: 'page',
      component: () => import('@/views/PageDetailView.vue'),
      props: true,
    },
    {
      path: '/:rest(.*)*',
      name: 'not-found',
      component: () => import('@/views/NotFoundView.vue'),
    },
  ],
  scrollBehavior(to, from, saved) {
    if (saved) return saved
    // Picking another journal keeps you where you are on the shelf.
    if (to.name === 'journal' && (from.name === 'journal' || from.name === 'library')) return false
    return { top: 0 }
  },
})
