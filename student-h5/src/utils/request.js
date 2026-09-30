/**
 * 统一 HTTP 请求封装（全项目唯一请求出口）
 * - 内部基于 uni.request，禁止页面 import axios/fetch
 * - 自动携带 Authorization: Bearer <token>
 * - 401 统一清登录态并跳登录页（可按请求关闭）
 * - 统一错误 toast（可按请求 silent）
 */
import { getToken, clearAuth } from '../store/user'

const BASE_URL = '/api'

/** 兜底错误文案（后端 error.message 优先） */
const FALLBACK_MESSAGES = {
  400: '请求参数有误',
  401: '登录已失效，请重新登录',
  403: '暂无权限访问',
  404: '资源不存在',
  409: '操作冲突，请刷新后重试',
  429: '操作过于频繁，请稍后再试',
  500: '服务器开小差了，请稍后重试',
  502: '服务暂不可用，请稍后重试',
  503: '服务维护中，请稍后重试',
}

const NETWORK_MSG = '网络异常，请检查网络后重试'

/**
 * 发起请求
 * @param {object} options
 * @param {string} options.url       接口路径（不含 /api 前缀，如 /auth/login）
 * @param {string} [options.method]  默认 GET
 * @param {object} [options.data]    body / query
 * @param {object} [options.header]  额外 header
 * @param {boolean} [options.auth]   是否带 token（默认 true）
 * @param {boolean} [options.silent] 是否抑制统一错误 toast（默认 false）
 * @param {boolean} [options.redirect401] 401 时是否跳登录页（默认 true）
 * @returns {Promise<any>} 成功 resolve 接口 data；失败 reject { statusCode, code, message }
 */
function request(options) {
  const {
    url,
    method = 'GET',
    data,
    header,
    auth = true,
    silent = false,
    redirect401 = true,
  } = options

  return new Promise((resolve, reject) => {
    const headers = { 'Content-Type': 'application/json', ...(header || {}) }
    if (auth) {
      const t = getToken()
      if (t) headers.Authorization = `Bearer ${t}`
    }

    uni.request({
      url: BASE_URL + url,
      method,
      data: data || {},
      header: headers,
      timeout: 15000,
      success: (res) => {
        const statusCode = res.statusCode
        if (statusCode >= 200 && statusCode < 300) {
          resolve(res.data)
          return
        }
        // 401：登录态失效
        if (statusCode === 401) {
          if (auth) {
            clearAuth()
            if (redirect401) {
              uni.showToast({ title: '登录已失效，请重新登录', icon: 'none' })
              setTimeout(() => {
                uni.reLaunch({ url: '/pages/login/index' })
              }, 800)
            }
          }
          reject(buildError(res, statusCode))
          return
        }
        const err = buildError(res, statusCode)
        if (!silent) {
          uni.showToast({ title: err.message || FALLBACK_MESSAGES[statusCode] || '请求失败', icon: 'none' })
        }
        reject(err)
      },
      fail: (failRes) => {
        if (!silent) {
          uni.showToast({ title: NETWORK_MSG, icon: 'none' })
        }
        reject({ statusCode: 0, code: 'NETWORK_ERROR', message: NETWORK_MSG, raw: failRes })
      },
    })
  })
}

function buildError(res, statusCode) {
  const errBody = res.data && res.data.error ? res.data.error : null
  return {
    statusCode,
    code: errBody ? errBody.code : `HTTP_${statusCode}`,
    message: (errBody && errBody.message) || FALLBACK_MESSAGES[statusCode] || '请求失败',
    raw: res,
  }
}

export default request

export const get = (url, data, options) => request({ url, method: 'GET', data, ...options })
export const post = (url, data, options) => request({ url, method: 'POST', data, ...options })
