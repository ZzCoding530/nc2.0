/**
 * 登录态管理（简单模块 store，token 持久化到 uni storage）
 * 响应式 student / token 供页面直接引用
 */
import { ref } from 'vue'

const TOKEN_KEY = 'niceoffer_token'
const STUDENT_KEY = 'niceoffer_student'

export const token = ref<string>('')
export const student = ref<Record<string, any> | null>(null)

let loaded = false

/** 从 uni storage 恢复登录态（幂等，App onLaunch 与各页 onLoad 均可调用） */
export function loadAuth(): void {
  if (loaded) return
  loaded = true
  try {
    const t = uni.getStorageSync(TOKEN_KEY)
    if (t) token.value = String(t)
    const s = uni.getStorageSync(STUDENT_KEY)
    if (s) {
      try {
        student.value = typeof s === 'string' ? JSON.parse(s) : s
      } catch (e) {
        student.value = null
      }
    }
  } catch (e) {
    // storage 异常时按未登录处理
  }
}

/** 获取 token（惰性从 storage 读取） */
export function getToken(): string {
  if (!loaded) loadAuth()
  return token.value
}

/** 写入登录态（内存 + storage 持久化） */
export function setAuth(t: string, s?: Record<string, any> | null): void {
  token.value = t
  if (s !== undefined && s !== null) student.value = s
  try {
    uni.setStorageSync(TOKEN_KEY, t)
    if (s) uni.setStorageSync(STUDENT_KEY, JSON.stringify(s))
  } catch (e) {
    // ignore
  }
}

/** 清除登录态（内存 + storage） */
export function clearAuth(): void {
  token.value = ''
  student.value = null
  try {
    uni.removeStorageSync(TOKEN_KEY)
    uni.removeStorageSync(STUDENT_KEY)
  } catch (e) {
    // ignore
  }
}

export function isLoggedIn(): boolean {
  return !!getToken()
}
