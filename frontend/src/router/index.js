import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('../views/CreateMeeting.vue'),
    meta: { title: '创建会议记录' },
  },
  {
    path: '/meeting/:id',
    name: 'MeetingDetail',
    component: () => import('../views/MeetingDetail.vue'),
    meta: { title: '会议记录详情' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 全局路由守卫 - 设置页面标题
router.beforeEach((to, from, next) => {
  document.title = to.meta.title || 'AWS Bedrock Minutes'
  next()
})

export default router
