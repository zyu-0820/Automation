import { createRouter, createWebHashHistory } from 'vue-router'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue'),
  },
  {
    path: '/',
    component: DefaultLayout,
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: '/servers' },
      {
        path: 'servers',
        name: 'Servers',
        component: () => import('@/views/ServersView.vue'),
      },
      {
        path: 'servers/:id',
        name: 'ServerDetail',
        component: () => import('@/views/ServerDetailView.vue'),
      },
      {
        path: 'services/:id/config',
        name: 'ServiceConfig',
        component: () => import('@/views/ServiceConfigView.vue'),
      },
      {
        path: 'services/:id/jars',
        name: 'ServiceJars',
        component: () => import('@/views/ServiceJarsView.vue'),
      },
      {
        path: 'multi-server',
        name: 'MultiServer',
        component: () => import('@/views/MultiServerView.vue'),
      },
      {
        path: 'operations',
        name: 'Operations',
        component: () => import('@/views/OperationLogsView.vue'),
      },
    ],
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()

  if (to.path === '/login') {
    // Redirect to home if already authenticated
    if (auth.isAuthenticated) return '/'
    return true
  }

  // Redirect to login if not authenticated
  if (!auth.isAuthenticated) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  return true
})

export default router
