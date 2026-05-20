import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/chat',
  },
  {
    path: '/chat',
    name: 'Chat',
    component: () => import('../components/ChatLayout.vue'),
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('../views/Dashboard.vue'),
  },
  {
    path: '/workout',
    name: 'Workout',
    component: () => import('../views/WorkoutLog.vue'),
  },
  {
    path: '/body',
    name: 'BodyMetric',
    component: () => import('../views/BodyMetric.vue'),
  },
  {
    path: '/diet',
    name: 'DietLog',
    component: () => import('../views/DietLog.vue'),
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

export default router
