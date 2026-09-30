<template>
  <view class="page-pad">
    <view class="brand">
      <text class="brand__name">注册账号</text>
      <text class="brand__slogan">使用开班名单中的邮箱注册</text>
    </view>

    <!-- 成功态：验证邮件已发送 -->
    <view v-if="sent" class="card sent-card">
      <text class="sent-card__icon">✉️</text>
      <text class="sent-card__title">验证邮件已发送</text>
      <text class="sent-card__desc">
        我们已向 <text class="sent-card__email">{{ sentEmail }}</text> 发送验证邮件，请在 24 小时内点击邮件中的链接完成激活。
      </text>
      <view class="btn btn-primary btn-block" @click="backToLogin">
        <text>返回登录</text>
      </view>
      <view class="resend" @click="resend">
        <text>{{ resendCooldown > 0 ? `未收到？${resendCooldown}s 后可重发` : '未收到邮件？重新发送' }}</text>
      </view>
    </view>

    <!-- 注册表单 -->
    <view v-else class="card">
      <view class="field">
        <text class="field-label">邮箱</text>
        <input
          v-model="form.email"
          class="field-input"
          type="text"
          placeholder="you@example.com"
          placeholder-class="ph"
          :maxlength="64"
        />
        <text v-if="errors.email" class="field-error">{{ errors.email }}</text>
      </view>

      <view class="field">
        <text class="field-label">姓名</text>
        <input
          v-model="form.name"
          class="field-input"
          type="text"
          placeholder="请输入真实姓名"
          placeholder-class="ph"
          :maxlength="32"
        />
        <text v-if="errors.name" class="field-error">{{ errors.name }}</text>
      </view>

      <view class="field">
        <text class="field-label">密码</text>
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

      <view class="btn btn-primary btn-block" :class="{ disabled: submitting }" @click="submit">
        <text>{{ submitting ? '提交中…' : '注册' }}</text>
      </view>

      <view class="login-links">
        <text class="link" @click="backToLogin">已有账号？返回登录</text>
      </view>
    </view>
  </view>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { post } from '../../utils/request'

const form = reactive({ email: '', name: '', password: '' })
const errors = reactive({ email: '', name: '', password: '' })
const submitting = ref(false)
const sent = ref(false)
const sentEmail = ref('')
const resendCooldown = ref(0)

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const PWD_RE = /^(?=.*[A-Za-z])(?=.*\d).{8,}$/

function validate() {
  errors.email = ''
  errors.name = ''
  errors.password = ''
  let ok = true
  if (!form.email.trim()) {
    errors.email = '请输入邮箱'
    ok = false
  } else if (!EMAIL_RE.test(form.email.trim())) {
    errors.email = '邮箱格式不正确'
    ok = false
  }
  if (!form.name.trim()) {
    errors.name = '请输入姓名'
    ok = false
  }
  if (!form.password) {
    errors.password = '请输入密码'
    ok = false
  } else if (!PWD_RE.test(form.password)) {
    errors.password = '密码至少 8 位，且需同时包含字母和数字'
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
      '/auth/register',
      { email: form.email.trim(), name: form.name.trim(), password: form.password },
      { auth: false, silent: true }
    )
    sentEmail.value = form.email.trim()
    sent.value = true
    startCooldown()
  } catch (err) {
    const code = err && err.code
    if (code === 'EMAIL_TAKEN') {
      errors.email = '该邮箱已注册，请直接登录'
    } else if (code === 'EMAIL_NOT_WHITELISTED') {
      errors.email = (err && err.message) || '该邮箱未在开班名单中，请联系班主任'
    } else {
      errors.password = (err && err.message) || '注册失败，请稍后重试'
    }
  } finally {
    submitting.value = false
  }
}

async function resend() {
  if (resendCooldown.value > 0) return
  try {
    await post('/auth/resend-verification', { email: sentEmail.value }, { auth: false, silent: true })
    uni.showToast({ title: '验证邮件已重新发送', icon: 'none' })
    startCooldown()
  } catch (err) {
    uni.showToast({ title: (err && err.message) || '发送失败，请稍后重试', icon: 'none' })
  }
}

function startCooldown() {
  resendCooldown.value = 60
  const timer = setInterval(() => {
    resendCooldown.value -= 1
    if (resendCooldown.value <= 0) clearInterval(timer)
  }, 1000)
}

function backToLogin() {
  uni.navigateBack({
    fail: () => {
      uni.reLaunch({ url: '/pages/login/index' })
    },
  })
}
</script>

<style scoped>
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
.sent-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 64rpx 32rpx;
}
.sent-card__icon {
  font-size: 64rpx;
}
.sent-card__title {
  margin-top: 24rpx;
  font-size: 32rpx;
  font-weight: 600;
  color: #111827;
}
.sent-card__desc {
  margin: 16rpx 0 40rpx;
  font-size: 26rpx;
  color: #6b7280;
  text-align: center;
  line-height: 1.7;
}
.sent-card__email {
  color: #4f46e5;
  font-weight: 600;
  word-break: break-all;
}
.login-links {
  display: flex;
  justify-content: center;
  margin-top: 28rpx;
  font-size: 26rpx;
}
.link {
  color: #4f46e5;
  font-weight: 500;
  padding: 8rpx 0;
}
.resend {
  margin-top: 24rpx;
  font-size: 24rpx;
  color: #9ca3af;
  padding: 8rpx 0;
}
</style>
