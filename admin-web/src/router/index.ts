import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { getToken } from '../utils/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/Login.vue'),
    meta: { title: '登录' },
  },
  {
    path: '/',
    component: () => import('../layout/AdminLayout.vue'),
    redirect: '/students',
    children: [
      {
        path: 'students',
        name: 'students',
        component: () => import('../views/Students.vue'),
        meta: { title: '学员管理' },
      },
      {
        path: 'schedules',
        name: 'schedules',
        component: () => import('../views/Schedules.vue'),
        meta: { title: '排期管理' },
      },
      {
        path: 'emails',
        name: 'emails',
        component: () => import('../views/Emails.vue'),
        meta: { title: '邮件中心' },
      },
      {
        path: 'preview',
        name: 'preview',
        component: () => import('../views/Preview.vue'),
        meta: { title: '学员视图预览' },
      },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/students' },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

router.beforeEach((to) => {
  const token = getToken()
  if (to.path !== '/login' && !token) {
    return {
      path: '/login',
      query: to.path === '/' ? {} : { redirect: to.fullPath },
    }
  }
  if (to.path === '/login' && token) {
    return { path: '/students' }
  }
  return true
})

router.afterEach((to) => {
  const title = to.meta.title
  document.title =
    typeof title === 'string' ? `${title} · NiceOffer 运营后台` : 'NiceOffer 运营后台'
})

export default router
