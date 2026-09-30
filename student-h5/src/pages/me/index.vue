<template>
  <view class="page-pad safe-bottom">
    <view class="page-title-row">
      <text class="page-title">我的</text>
    </view>

    <!-- 账号卡 -->
    <view class="card">
      <view class="account-row">
        <view class="account-avatar">
          <text>{{ avatarChar }}</text>
        </view>
        <view class="account-info">
          <text class="account-info__name">{{ me.student?.name || '同学' }}</text>
          <text v-if="me.student?.cohort" class="account-info__cohort">{{ me.student.cohort }}</text>
        </view>
      </view>
      <view class="info-row">
        <text class="info-row__label">邮箱（通知地址）</text>
        <text class="info-row__value">{{ me.student?.email || '—' }}</text>
      </view>
      <view class="info-row">
        <text class="info-row__label">班期</text>
        <text class="info-row__value">{{ me.student?.cohort || '—' }}</text>
      </view>
      <view class="info-row info-row--link" @click="goForgot">
        <text class="info-row__label">密码</text>
        <text class="info-row__value info-row__value--action">重置（邮件验证）›</text>
      </view>
    </view>

    <!-- 清单卡 -->
    <view class="card">
      <text class="card-title">学习清单</text>
      <view class="list-row">
        <view class="list-row__texts">
          <text class="list-row__title">数据结构自学清单</text>
          <text class="list-row__sub">按清单自查补齐基础</text>
        </view>
        <ExternalLink v-if="links.ds_checklist_url" inline :url="links.ds_checklist_url" label="查看" />
        <text v-else class="coming">即将上线</text>
      </view>
      <view class="list-row">
        <view class="list-row__texts">
          <text class="list-row__title">AI 岗刷题 SOP</text>
          <text class="list-row__sub">面试高频题型与刷题路径</text>
        </view>
        <ExternalLink v-if="links.brush_sop_url" inline :url="links.brush_sop_url" label="查看" />
        <text v-else class="coming">即将上线</text>
      </view>
    </view>

    <!-- 退出登录 -->
    <view class="card">
      <view class="logout-btn" @click="confirmLogoutVisible = true">
        <text>退出登录</text>
      </view>
    </view>

    <!-- 退出确认弹层 -->
    <view v-if="confirmLogoutVisible" class="mask" @click="confirmLogoutVisible = false">
      <view class="confirm" @click.stop>
        <text class="confirm__title">退出登录？</text>
        <text class="confirm__desc">退出后需要重新输入邮箱密码登录。</text>
        <view class="confirm__btns">
          <view class="confirm__btn confirm__btn--plain" @click="confirmLogoutVisible = false">
            <text>取消</text>
          </view>
          <view class="confirm__btn confirm__btn--primary" @click="doLogout">
            <text>{{ loggingOut ? '退出中…' : '退出' }}</text>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { get } from '../../utils/request'
import { clearAuth, loadAuth } from '../../store/user'
import ExternalLink from '../../components/ExternalLink.vue'

const me = reactive({ student: null, links: {} })
const confirmLogoutVisible = ref(false)
const loggingOut = ref(false)

const links = computed(() => me.links || {})
const avatarChar = computed(() => (me.student && me.student.name ? me.student.name.slice(0, 1) : '学'))

async function fetchMe() {
  try {
    const res = await get('/me')
    me.student = res.student || null
    me.links = res.links || {}
  } catch (e) {
    // 401 已由 request 统一跳登录
  }
}

onShow(() => {
  loadAuth()
  fetchMe()
})

function goForgot() {
  // 改密走邮件重置：跳登录页的忘记密码流程
  uni.navigateTo({
    url: '/pages/login/index?forgot=1',
    fail: () => {
      uni.reLaunch({ url: '/pages/login/index?forgot=1' })
    },
  })
}

function doLogout() {
  if (loggingOut.value) return
  loggingOut.value = true
  clearAuth()
  confirmLogoutVisible.value = false
  uni.reLaunch({ url: '/pages/login/index' })
}
</script>

<style scoped>
.page-title-row {
  padding: 8rpx 8rpx 28rpx;
}
.page-title {
  font-size: 40rpx;
  font-weight: 700;
  color: #111827;
}
.account-row {
  display: flex;
  align-items: center;
  padding-bottom: 28rpx;
  border-bottom: 2rpx solid #f3f4f6;
}
.account-avatar {
  width: 112rpx;
  height: 112rpx;
  border-radius: 999rpx;
  background: #eef2ff;
  color: #4f46e5;
  font-size: 44rpx;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 24rpx;
}
.account-info {
  display: flex;
  flex-direction: column;
}
.account-info__name {
  font-size: 34rpx;
  font-weight: 700;
  color: #111827;
}
.account-info__cohort {
  margin-top: 8rpx;
  font-size: 24rpx;
  color: #6b7280;
}
.info-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 88rpx;
  border-bottom: 2rpx solid #f3f4f6;
}
.info-row:last-child {
  border-bottom: none;
}
.info-row__label {
  font-size: 28rpx;
  color: #374151;
}
.info-row__value {
  font-size: 28rpx;
  color: #111827;
  text-align: right;
}
.info-row--link:active {
  opacity: 0.6;
}
.info-row__value--action {
  color: #4f46e5;
  font-weight: 500;
}
.list-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 26rpx 0;
  border-bottom: 2rpx solid #f3f4f6;
}
.list-row:last-child {
  border-bottom: none;
}
.list-row__texts {
  flex: 1;
  min-width: 0;
  margin-right: 16rpx;
  display: flex;
  flex-direction: column;
}
.list-row__title {
  font-size: 28rpx;
  color: #111827;
}
.list-row__sub {
  margin-top: 6rpx;
  font-size: 24rpx;
  color: #9ca3af;
}
.coming {
  font-size: 24rpx;
  color: #9ca3af;
  background: #f3f4f6;
  border-radius: 999rpx;
  padding: 8rpx 20rpx;
}
.logout-btn {
  min-height: 88rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #dc2626;
  font-size: 30rpx;
  font-weight: 600;
}
.logout-btn:active {
  opacity: 0.6;
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
  align-items: center;
  justify-content: center;
}
.confirm {
  width: 580rpx;
  box-sizing: border-box;
  background: #ffffff;
  border-radius: 24rpx;
  padding: 48rpx 36rpx 36rpx;
  display: flex;
  flex-direction: column;
}
.confirm__title {
  font-size: 32rpx;
  font-weight: 700;
  color: #111827;
  text-align: center;
}
.confirm__desc {
  margin-top: 16rpx;
  font-size: 26rpx;
  color: #6b7280;
  text-align: center;
  line-height: 1.6;
}
.confirm__btns {
  display: flex;
  gap: 20rpx;
  margin-top: 40rpx;
}
.confirm__btn {
  flex: 1;
  min-height: 88rpx;
  border-radius: 16rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28rpx;
  font-weight: 600;
}
.confirm__btn--plain {
  background: #f3f4f6;
  color: #374151;
}
.confirm__btn--primary {
  background: #dc2626;
  color: #ffffff;
}
.confirm__btn:active {
  opacity: 0.75;
}
</style>
