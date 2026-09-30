<template>
  <view class="page-pad reset-page">
    <view class="brand">
      <text class="brand__name">重置密码</text>
      <text class="brand__slogan">为你的账号设置新登录密码</text>
    </view>

    <!-- 成功态：密码已更新 -->
    <view v-if="state === 'success'" class="card state-card">
      <text class="state-card__icon state-card__icon--ok">✓</text>
      <text class="state-card__title">密码已更新</text>
      <text class="state-card__desc">新密码已生效，请使用新密码重新登录。</text>
      <view class="btn btn-primary btn-block" @click="goLogin">
        <text>去登录</text>
      </view>
    </view>

    <!-- 错误态：token 缺失 / 无效 / 过期 -->
    <view v-else-if="state === 'expired' || state === 'invalid'" class="card state-card">
      <text class="state-card__icon state-card__icon--warn">{{ state === 'expired' ? '⏳' : '✕' }}</text>
      <text class="state-card__title">{{ state === 'expired' ? '重置链接已过期' : '重置链接无效' }}</text>
      <text class="state-card__desc">
        {{ state === 'expired' ? '链接有效期 24 小时，已过期。请重新获取重置邮件。' : '链接可能已被使用或不存在，请从最新邮件中的链接重新打开。' }}
      </text>
      <view class="btn btn-primary btn-block" @click="goForgot">
        <text>重新获取重置邮件</text>
      </view>
      <view class="resend" @click="goLogin">
        <text>返回登录</text>
      </view>
    </view>

    <!-- 重置表单 -->
    <view v-else class="card">
      <view class="field">
        <text class="field-label">新密码</text>
        <input
          v-model="form.password"
          class="field-input"
          :password="true"
          placeholder="至少 8 位，需包含字母和数字"
          placeholder-class="ph"
          :maxlength="64"
        />
        <text v-if="errors.password" class="field-error">{{ errors.password }}</text>
      </view>

      <view class="field">
        <text class="field-label">确认新密码</text>
        <input
          v-model="form.confirm"
          class="field-input"
          :password="true"
          placeholder="请再次输入新密码"
          placeholder-class="ph"
          :maxlength="64"
        />
        <text v-if="errors.confirm" class="field-error">{{ errors.confirm }}</text>
      </view>

      <view class="btn btn-primary btn-block" :class="{ disabled: submitting }" @click="submit">
        <text>{{ submitting ? '提交中…' : '重置密码' }}</text>
      </view>

      <view class="note">重置链接有效期 24 小时，每个链接只能使用一次。</view>
    </view>
  </view>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { post } from '../../utils/request'

const state = ref('form') // form | success | expired | invalid
const token = ref('')
const form = reactive({ password: '', confirm: '' })
const errors = reactive({ password: '', confirm: '' })
const submitting = ref(false)

const PWD_RE = /^(?=.*[A-Za-z])(?=.*\d).{8,}$/

onLoad((options) => {
  token.value = (options && options.token) || ''
  if (!token.value) {
    state.value = 'invalid'
  }
})

function validate() {
  errors.password = ''
  errors.confirm = ''
  let ok = true
  if (!form.password) {
    errors.password = '请输入新密码'
    ok = false
  } else if (!PWD_RE.test(form.password)) {
    errors.password = '密码至少 8 位，且需同时包含字母和数字'
    ok = false
  }
  if (!form.confirm) {
    errors.confirm = '请再次输入新密码'
    ok = false
  } else if (form.confirm !== form.password) {
    errors.confirm = '两次输入的密码不一致'
    ok = false
  }
  return ok
}

async function submit() {
  if (submitting.value) return
  if (!validate()) return
  submitting.value = true
  try {
    await post(
      '/auth/reset-password',
      { token: token.value, new_password: form.password },
      { auth: false, silent: true }
    )
    state.value = 'success'
  } catch (err) {
    const code = err && err.code
    if (code === 'TOKEN_EXPIRED') {
      state.value = 'expired'
    } else if (code === 'TOKEN_INVALID') {
      state.value = 'invalid'
    } else {
      errors.password = (err && err.message) || '重置失败，请稍后重试'
    }
  } finally {
    submitting.value = false
  }
}

function goLogin() {
  uni.reLaunch({ url: '/pages/login/index' })
}

function goForgot() {
  // 登录页 ?forgot=1 会自动弹出「忘记密码」弹层
  uni.reLaunch({ url: '/pages/login/index?forgot=1' })
}
</script>

<style scoped>
.reset-page {
  min-height: 100vh;
  box-sizing: border-box;
}
.ph {
  color: #9ca3af;
}
.brand {
  padding: 72rpx 16rpx 40rpx;
  display: flex;
  flex-direction: column;
}
.brand__name {
  font-size: 44rpx;
  font-weight: 700;
  color: #111827;
}
.brand__slogan {
  margin-top: 12rpx;
  font-size: 26rpx;
  color: #6b7280;
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
.resend {
  margin-top: 24rpx;
  font-size: 24rpx;
  color: #9ca3af;
  padding: 8rpx 0;
}
</style>
