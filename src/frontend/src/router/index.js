/**
 * Vue Router: single chat route; syncs document title from route meta.
 */
import { createRouter, createWebHistory } from 'vue-router'
import ChatView from '@/views/ChatView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'chat',
      component: ChatView,
      meta: { title: 'Expert Agent — Flink Studies' }
    }
  ]
})

/** @param {import('vue-router').RouteLocationNormalized} to */
router.beforeEach((to, _from, next) => {
  document.title = to.meta.title || 'Expert Agent — Flink Studies'
  next()
})

export default router
