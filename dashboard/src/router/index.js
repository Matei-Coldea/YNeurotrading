import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('../views/DashboardView.vue'),
  },
  {
    path: '/opportunity/:id',
    name: 'OpportunityDetail',
    component: () => import('../views/OpportunityDetailView.vue'),
    props: true,
  },
  {
    path: '/opportunity/:id/simulation',
    name: 'SimulationPipeline',
    component: () => import('../views/SimulationPipelineView.vue'),
    props: true,
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
