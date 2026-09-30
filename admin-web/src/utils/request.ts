import axios from 'axios'
import type { AxiosError, AxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'
import { clearToken, getToken } from './auth'

interface ApiErrorBody {
  error?: { code?: string; message?: string }
}

function extractErrorMessage(
  data: ApiErrorBody | undefined,
  status: number,
  fallback: string,
): string {
  const message = data?.error?.message
  if (message) return message
  if (status === 401) return '登录已失效，请重新登录'
  if (status === 403) return '没有权限执行此操作'
  if (status === 404) return '请求的资源不存在'
  if (status >= 500) return '服务器开小差了，请稍后重试'
  return fallback
}

const instance = axios.create({
  baseURL: '/api',
  timeout: 20000,
})

instance.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

instance.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiErrorBody>) => {
    const status = error.response?.status
    // 401：登录态失效（登录页本身的 401 = 账号密码错误，走统一错误提示）
    if (status === 401 && router.currentRoute.value.path !== '/login') {
      clearToken()
      ElMessage.warning('登录已失效，请重新登录')
      router.push('/login')
      return Promise.reject(error)
    }
    const message = status
      ? extractErrorMessage(
          error.response?.data,
          status,
          `请求失败（HTTP ${status}）`,
        )
      : '网络连接失败，请检查网络后重试'
    ElMessage.error(message)
    return Promise.reject(error)
  },
)

export async function request<T>(config: AxiosRequestConfig): Promise<T> {
  const response = await instance.request<T>(config)
  return response.data
}

export function get<T>(url: string, params?: Record<string, unknown>): Promise<T> {
  return request<T>({ url, method: 'get', params })
}

export function post<T>(url: string, data?: unknown): Promise<T> {
  return request<T>({ url, method: 'post', data })
}

export function put<T>(url: string, data?: unknown): Promise<T> {
  return request<T>({ url, method: 'put', data })
}
