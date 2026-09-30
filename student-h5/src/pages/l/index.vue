<template>
  <view class="page-pad l-page">
    <!-- 加载中 -->
    <view v-if="state === 'loading'" class="card state-card">
      <text class="state-card__title">正在打开直达链接…</text>
      <text class="state-card__desc">免登录跳转中，请稍候</text>
    </view>

    <!-- 失败 -->
    <view v-else-if="state === 'invalid'" class="card state-card">
      <text class="state-card__icon state-card__icon--warn">✕</text>
      <text class="state-card__title">链接已失效</text>
      <text class="state-card__desc">直达链接已过期或已被使用（有效期 7 天）。请从邮件中重新打开，或登录后查看。</text>
      <view class="btn btn-primary btn-block" @click="goLogin">
        <text>去登录</text>
      </view>
      <view class="btn btn-plain btn-block state-card__alt" @click="goHomeIfLoggedIn">
        <text>我已登录，进入首页</text>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { get } from '../../utils/request'
import { setAuth, isLoggedIn } from '../../store/user'

const state = ref('loading')

onLoad(async (options) => {
  const token = (options && options.token) || ''
  // 目标路由（已 encodeURIComponent 编码，如 %2Fpages%2Flesson%2Findex%3Fcode%3DT01）
  let to = ''
  if (options && options.to) {
    try {
      to = decodeURIComponent(options.to)
    } catch (e) {
      to = options.to
    }
  }
  // to 缺省或非本站页面路径时回首页
  if (!to || to.indexOf('/pages/') !== 0) {
    to = '/pages/home/index'
  }
  if (!token) {
    if (isLoggedIn()) {
      redirect(to)
    } else {
      goLogin()
    }
    return
  }
  try {
    // token 换 JWT（7 天有效），存本地后直达目标页
    const res = await get(`/links/magic/${encodeURIComponent(token)}`, {}, { auth: false, silent: true })
    if (res && res.token) {
      setAuth(res.token, res.student || null)
      redirect(to)
    } else {
      state.value = 'invalid'
    }
  } catch (err) {
    state.value = 'invalid'
  }
})

function redirect(to) {
  uni.reLaunch({
    url: to,
    fail: () => {
      // 目标路由异常时兜底回首页
      uni.reLaunch({ url: '/pages/home/index' })
    },
  })
}

function goLogin() {
  uni.reLaunch({ url: '/pages/login/index' })
}

function goHomeIfLoggedIn() {
  if (isLoggedIn()) {
    redirect('/pages/home/index')
  } else {
    goLogin()
  }
}
</script>

<style scoped>
.l-page {
  min-height: 100vh;
  box-sizing: border-box;
  padding-top: 120rpx;
}
.state-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 72rpx 32rpx;
}
.state-card__icon {
  width: 120rpx;
  height: 120rpx;
  border-radius: 999rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 56rpx;
  background: #fef3c7;
  color: #f59e0b;
}
.state-card__title {
  margin-top: 32rpx;
  font-size: 34rpx;
  font-weight: 700;
  color: #111827;
}
.state-card__desc {
  margin: 16rpx 0 48rpx;
  font-size: 26rpx;
  color: #6b7280;
  text-align: center;
  line-height: 1.7;
}
.state-card__alt {
  margin-top: 20rpx;
}
</style>
