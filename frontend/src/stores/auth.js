import { defineStore } from 'pinia'

import http from '@/api/http'
import { useChatStore } from '@/stores/chat'
import { useDocumentsStore } from '@/stores/documents'

// 登录状态：令牌和用户信息持久化到 localStorage，刷新页面不丢失
export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    user: JSON.parse(localStorage.getItem('user') || 'null'),
  }),
  getters: {
    isLoggedIn: (s) => !!s.token,
    isAdmin: (s) => s.user?.role === 'admin',
  },
  actions: {
    async login(username, password) {
      const { data } = await http.post('/auth/login', { username, password })
      this.token = data.access_token
      this.user = data.user
      localStorage.setItem('token', data.access_token)
      localStorage.setItem('user', JSON.stringify(data.user))
      // 登录新账号后清空界面状态，防止上一个用户的数据残留显示
      this._resetStores()
    },
    async register(username, password) {
      await http.post('/auth/register', { username, password })
    },
    async fetchMe() {
      const { data } = await http.get('/auth/me')
      this.user = data
      localStorage.setItem('user', JSON.stringify(data))
    },
    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      // 退出登录时同步清空聊天/知识库界面状态
      this._resetStores()
    },
    _resetStores() {
      useChatStore().reset()
      useDocumentsStore().reset()
    },
  },
})
