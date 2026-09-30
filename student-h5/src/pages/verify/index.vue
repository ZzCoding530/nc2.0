<template>
  <view class="page-pad verify-page">
    <!-- 加载中 -->
    <view v-if="state === 'loading'" class="card state-card">
      <text class="state-card__title">正在验证邮箱…</text>
      <text class="state-card__desc">请稍候</text>
    </view>

    <!-- 成功 -->
    <view v-else-if="state === 'success'" class="card state-card">
      <text class="state-card__icon state-card__icon--ok">✓</text>
      <text class="state-card__title">邮箱验证成功</text>
      <text class="state-card__desc">
        {{ studentInfo.name ? `${studentInfo.name}，欢迎加入 NiceOffer` : '欢迎加入 NiceOffer' }}
        <text v-if="studentInfo.cohort">（{{ studentInfo.cohort }}）</text>
      </text>
      <view class="btn btn-primary btn-block" @click="goHome">
        <text>进入学员中心</text>
      </view>
    </view>

    <!-- 已过期 -->
    <view v-else-if="state === 'expired'" class="card state-card">
      <text class="state-card__icon state-card__icon--warn">⏳</text>
      <text class="state-card__title">验证链接已过期</text>
      <text class="state-card__desc">链接有效期 24 小时。请重新注册或联系班主任协助。</text>
      <view class="btn btn-primary btn-block" @click="goLogin">
        <text>返回登录</text>
      </view>
    </view>

    <!-- 无效 / 失败 -->
    <view v-else class="card state-card">
      <text class="state-card__icon state-card__icon--warn">✕</text>
      <text class="state-card__title">验证链接无效</text>
      <text class="state-card__desc">链接可能已被使用或不存在。请从最新邮件中的链接重新打开。</text>
      <view class="btn btn-primary btn-block" @click="goLogin">
        <text>返回登录</text>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { post } from '../../utils/request'
import { setAuth } from '../../store/user'

const state = ref('loading') // loading | success | expired | invalid
const studentInfo = reactive({ name: '', cohort: '' })

onLoad(async (options) => {
  const token = (options && options.token) || ''
  if (!token) {
    state.value = 'invalid'
    return
  }
  try {
    // 成功即自动签发 JWT（免再登录）
    const res = await post(`/auth/verify/${encodeURIComponent(token)}`, {}, { auth: false, silent: true })
    setAuth(res.token, res.student || null)
    if (res.student) {
      studentInfo.name = res.student.name || ''
      studentInfo.cohort = res.student.cohort || ''
    }
    state.value = 'success'
  } catch (err) {
    if (err && err.code === 'TOKEN_EXPIRED') {
      state.value = 'expired'
    } else {
      state.value = 'invalid'
    }
  }
})

function goHome() {
  uni.reLaunch({ url: '/pages/home/index' })
}

function goLogin() {
  uni.reLaunch({ url: '/pages/login/index' })
}
</script>

<style scoped>
.verify-page {
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
}
.state-card__icon--ok {
  background: #f0fdf4;
  color: #16a34a;
}
.state-card__icon--warn {
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
</style>
