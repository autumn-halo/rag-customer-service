import axios from 'axios'
import { ElMessage } from 'element-plus'

// 统一的请求客户端：自动带登录令牌、统一处理错误
const http = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.response.use(
  (resp) => resp,
  async (error) => {
    // 登录过期：清掉本地凭证，跳回登录页
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      const { default: router } = await import('@/router')
      if (router.currentRoute.value.name !== 'login') {
        router.push({ name: 'login' })
      }
    }
    const detail = error.response?.data?.detail
    ElMessage.error(typeof detail === 'string' ? detail : '网络异常，请稍后重试')
    return Promise.reject(error)
  },
)

export default http
