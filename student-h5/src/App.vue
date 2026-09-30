<script>
import { loadAuth } from './store/user'

export default {
  onLaunch: function () {
    // 启动时从 uni storage 恢复登录态
    loadAuth()
  },
  onShow: function () {},
  onHide: function () {},
}
</script>

<style>
/* ===== 全局基础 ===== */
page {
  background: #f3f4f6;
  font-size: 28rpx; /* 14px 正文 */
  color: #111827;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}

/* ===== 布局 ===== */
.page-pad {
  padding: 24rpx 24rpx 48rpx;
}
.safe-bottom {
  padding-bottom: calc(48rpx + constant(safe-area-inset-bottom));
  padding-bottom: calc(48rpx + env(safe-area-inset-bottom));
}

/* ===== 卡片 ===== */
.card {
  background: #ffffff;
  border-radius: 24rpx;
  padding: 32rpx;
  margin-bottom: 24rpx;
  box-shadow: 0 2rpx 12rpx rgba(17, 24, 39, 0.04);
}
.card-title {
  font-size: 30rpx;
  font-weight: 600;
  color: #111827;
}
.card-sub {
  font-size: 24rpx; /* 12px 辅助（≥11px） */
  color: #9ca3af;
  margin-top: 6rpx;
}

/* ===== chip ===== */
.chip {
  display: inline-flex;
  align-items: center;
  padding: 6rpx 20rpx;
  border-radius: 999rpx;
  font-size: 24rpx;
  line-height: 1.5;
  background: #f3f4f6;
  color: #6b7280;
}
.chip-brand {
  background: #eef2ff;
  color: #4f46e5;
}
.chip-green {
  background: #f0fdf4;
  color: #16a34a;
}
.chip-mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, 'Courier New', monospace;
}

/* ===== 按钮（高度≥88rpx=44px） ===== */
.btn {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 88rpx;
  padding: 0 32rpx;
  border-radius: 16rpx;
  font-size: 28rpx;
  font-weight: 600;
  text-align: center;
  box-sizing: border-box;
}
.btn-primary {
  background: #4f46e5;
  color: #ffffff;
}
.btn-primary:active {
  background: #4338ca;
}
.btn-primary.disabled {
  background: #c7d2fe;
  color: #ffffff;
}
.btn-ghost {
  background: #eef2ff;
  color: #4f46e5;
}
.btn-ghost:active {
  background: #e0e7ff;
}
.btn-plain {
  background: #f3f4f6;
  color: #374151;
}
.btn-block {
  width: 100%;
}

/* ===== 表单 ===== */
.field {
  margin-bottom: 28rpx;
}
.field-label {
  font-size: 26rpx;
  color: #374151;
  margin-bottom: 12rpx;
  display: block;
}
.field-input {
  width: 100%;
  min-height: 88rpx;
  box-sizing: border-box;
  padding: 20rpx 24rpx;
  border: 2rpx solid #e5e7eb;
  border-radius: 16rpx;
  background: #ffffff;
  font-size: 28rpx;
  color: #111827;
}
.field-error {
  font-size: 24rpx;
  color: #dc2626;
  margin-top: 8rpx;
  min-height: 32rpx;
  line-height: 1.4;
}

/* ===== note 提示条 ===== */
.note {
  font-size: 24rpx;
  color: #9ca3af;
  line-height: 1.5;
  padding: 16rpx 0 0;
}

/* ===== 骨架屏 ===== */
.skeleton {
  position: relative;
  overflow: hidden;
  background: #e5e7eb;
  border-radius: 12rpx;
}
.skeleton::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(90deg, rgba(255, 255, 255, 0) 0%, rgba(255, 255, 255, 0.6) 50%, rgba(255, 255, 255, 0) 100%);
  transform: translateX(-100%);
  animation: skeleton-wave 1.4s ease infinite;
}
@keyframes skeleton-wave {
  100% {
    transform: translateX(100%);
  }
}

/* ===== 分隔线 ===== */
.divider {
  height: 2rpx;
  background: #f3f4f6;
  margin: 24rpx 0;
}

/* ===== 通用 mono 字体 ===== */
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, 'Courier New', monospace;
}
</style>
