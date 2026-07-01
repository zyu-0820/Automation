import { createRouter, createWebHashHistory } from 'vue-router'
import DefaultLayout from '@/layouts/DefaultLayout.vue'

const routes = [
  {
    path: '/',
    component: DefaultLayout,
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

export default router
