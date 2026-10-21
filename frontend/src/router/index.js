import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { public: true },
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('@/views/RegisterView.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    children: [
      { path: '', name: 'chat', component: () => import('@/views/ChatView.vue') },
      { path: 'profile', name: 'profile', component: () => import('@/views/ProfileView.vue') },
      {
        path: 'knowledge',
        name: 'knowledge',
        component: () => import('@/views/KnowledgeBaseView.vue'),
        meta: { requiresAdmin: true },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫：未登录 → 登录页；已登录访问登录页 → 聊天页；非管理员 → 拒绝进管理页
router.beforeEach((to) => {
  const token = localStorage.getItem('token')
  if (!to.meta.public && !token) {
    return { name: 'login' }
  }
  if (to.name === 'login' && token) {
    return { name: 'chat' }
  }
  if (to.meta.requiresAdmin) {
    const user = JSON.parse(localStorage.getItem('user') || 'null')
    if (user?.role !== 'admin') {
      return { name: 'chat' }
    }
  }
})

export default router
