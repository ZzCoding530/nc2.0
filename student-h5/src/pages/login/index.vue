<template>
  <view class="page-pad login-page">
    <!-- 品牌区 -->
    <view class="brand">
      <text class="brand__name">NiceOffer 学员中心</text>
      <text class="brand__slogan">班课交付系统 · 学员端</text>
    </view>

    <!-- 锁定态：连续 5 次密码错误，只显示「请查收邮件」 -->
    <view v-if="locked" class="card locked-card">
      <text class="locked-card__icon">✉️</text>
      <text class="locked-card__title">登录已锁定</text>
      <text class="locked-card__desc">密码错误次数过多，账号已临时锁定 10 分钟。重置说明已发送到你的邮箱，请查收邮件。</text>
      <view class="btn btn-ghost btn-block" @click="openForgot">
        <text>重新发送重置邮件</text>
      </view>
    </view>

    <!-- 登录表单 -->
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
        <text class="field-label">密码</text>
        <input
          v-model="form.password"
          class="field-input"
          :password="true"
          placeholder="请输入密码"
          placeholder-class="ph"
          :maxlength="64"
        />
        <text v-if="errors.password" class="field-error">{{ errors.password }}</text>
      </view>

      <view class="btn btn-primary btn-block" :class="{ disabled: submitting }" @click="submit">
        <text>{{ submitting ? '登录中…' : '登录' }}</text>
      </view>

      <view class="login-links">
        <text class="link" @click="openForgot">忘记密码？</text>
        <text class="link link--brand" @click="goRegister">没有账号？注册</text>
      </view>
    </view>

    <!-- 忘记密码弹层 -->
    <view v-if="forgotVisible" class="mask" @click="closeForgot">
      <view class="sheet" @click.stop>
        <text class="sheet__title">重置密码</text>
        <text class="sheet__desc">输入注册邮箱，我们将发送密码重置链接（24 小时内有效）。</text>
        <input
          v-model="forgotEmail"
          class="field-input"
          type="text"
          placeholder="you@example.com"
          placeholder-class="ph"
          :maxlength="64"
        />
        <text v-if="forgotSent" class="field-ok">重置邮件已发送，请查收（未收到请检查垃圾箱）。</text>
        <view class="btn btn-primary btn-block" :class="{ disabled: forgotSending }" @click="sendReset">
          <text>{{ forgotSent ? '再发一次' : forgotSending ? '发送中…' : '发送重置邮件' }}</text>
        </view>
        <view class="btn btn-plain btn-block sheet__close" @click="closeForgot">
          <text>关闭</text>
        </view>
      </view>
    </view>

    <!-- 底部固定文案 -->
    <view class="login-footer">
      <text>微信一键登录将在小程序版上线后开放</text>
    </view>
  </view>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { post } from '../../utils/request'
import { setAuth } from '../../store/user'

const form = reactive({ email: '', password: '' })
const errors = reactive({ email: '', password: '' })
const submitting = ref(false)
const locked = ref(false)

const forgotVisible = ref(false)
const forgotEmail = ref('')
const forgotSent = ref(false)
const forgotSending = ref(false)

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

onLoad((options) => {
  // me 页「改密码」跳转：?forgot=1 自动弹重置弹层
  if (options && options.forgot === '1') {
    forgotVisible.value = true
  }
})

function validate() {
  errors.email = ''
  errors.password = ''
  let ok = true
  if (!form.email.trim()) {
    errors.email = '请输入邮箱'
    ok = false
  } else if (!EMAIL_RE.test(form.email.trim())) {
    errors.email = '邮箱格式不正确'
    ok = false
  }
  if (!form.password) {
    errors.password = '请输入密码'
    ok = false
  }
  return ok
}

async function submit() {
  if (submitting.value) return
  if (!validate()) return
  submitting.value = true
  try {
    const res = await post(
      '/auth/login',
      { email: form.email.trim(), password: form.password },
      { auth: false, silent: true }
    )
    setAuth(res.token, res.student)
    uni.reLaunch({ url: '/pages/home/index' })
  } catch (err) {
    if (err && err.code === 'ACCOUNT_LOCKED') {
      // 连续 5 次失败锁 10 分钟：锁定态只显示「请查收邮件」
      locked.value = true
    } else if (err && err.code === 'ACCOUNT_PENDING') {
      errors.password = '账号未激活，请先查收验证邮件'
    } else if (err && err.code === 'INVALID_CREDENTIALS') {
      errors.password = '邮箱或密码不正确'
    } else {
      errors.password = (err && err.message) || '登录失败，请稍后重试'
    }
  } finally {
    submitting.value = false
  }
}

function openForgot() {
  if (!forgotVisible.value) {
    forgotVisible.value = true
    forgotSent.value = false
    forgotEmail.value = form.email || ''
  }
}

function closeForgot() {
  forgotVisible.value = false
}

async function sendReset() {
  if (forgotSending.value) return
  const email = forgotEmail.value.trim()
  if (!EMAIL_RE.test(email)) {
    uni.showToast({ title: '请输入正确的邮箱', icon: 'none' })
    return
  }
  forgotSending.value = true
  try {
    await post('/auth/forgot-password', { email }, { auth: false, silent: true })
    forgotSent.value = true
    locked.value = false
  } catch (err) {
    uni.showToast({ title: (err && err.message) || '发送失败，请稍后重试', icon: 'none' })
  } finally {
    forgotSending.value = false
  }
}

function goRegister() {
  uni.navigateTo({ url: '/pages/register/index' })
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
}
.ph {
  color: #9ca3af;
}
.brand {
  padding: 96rpx 16rpx 48rpx;
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
.locked-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 64rpx 32rpx;
}
.locked-card__icon {
  font-size: 64rpx;
}
.locked-card__title {
  margin-top: 24rpx;
  font-size: 32rpx;
  font-weight: 600;
  color: #111827;
}
.locked-card__desc {
  margin: 16rpx 0 40rpx;
  font-size: 26rpx;
  color: #6b7280;
  text-align: center;
  line-height: 1.6;
}
.login-links {
  display: flex;
  justify-content: space-between;
  margin-top: 28rpx;
  font-size: 26rpx;
}
.link {
  color: #6b7280;
  padding: 8rpx 0;
}
.link--brand {
  color: #4f46e5;
  font-weight: 500;
}
.login-footer {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 20rpx 24rpx calc(20rpx + env(safe-area-inset-bottom));
  text-align: center;
  font-size: 24rpx;
  color: #9ca3af;
  background: rgba(243, 244, 246, 0.9);
}
.mask {
  position: fixed;
  left: 0;
  right: 0;
  top: 0;
  bottom: 0;
  background: rgba(17, 24, 39, 0.45);
  z-index: 999;
  display: flex;
  align-items: flex-end;
}
.sheet {
  width: 100%;
  box-sizing: border-box;
  background: #ffffff;
  border-radius: 32rpx 32rpx 0 0;
  padding: 40rpx 32rpx calc(40rpx + env(safe-area-inset-bottom));
  display: flex;
  flex-direction: column;
}
.sheet__title {
  font-size: 34rpx;
  font-weight: 700;
  color: #111827;
}
.sheet__desc {
  margin: 12rpx 0 28rpx;
  font-size: 26rpx;
  color: #6b7280;
  line-height: 1.6;
}
.sheet__close {
  margin-top: 20rpx;
}
.field-ok {
  margin-top: 12rpx;
  font-size: 26rpx;
  color: #16a34a;
  line-height: 1.5;
}
</style>
