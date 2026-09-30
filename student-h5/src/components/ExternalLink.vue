<template>
  <view
    class="ext-link"
    :class="[inline ? 'ext-link--inline' : 'ext-link--btn', ghost ? 'ext-link--ghost' : '']"
    :hover-class="inline ? 'ext-link--hover' : ''"
    :hover-stay-time="80"
    @click="open"
  >
    <text class="ext-link__label">{{ label }}</text>
    <text v-if="inline" class="ext-link__arrow">›</text>
  </view>
</template>

<script setup>
/**
 * 外链统一出口：
 * - H5：window.open 新窗口打开
 * - 小程序等其他端：复制链接并 toast 提示
 */
const props = defineProps({
  url: { type: String, default: '' },
  label: { type: String, default: '' },
  /** inline=胶囊内联样式；默认为块级按钮样式（≥44px 高） */
  inline: { type: Boolean, default: false },
  /** ghost=浅品牌底按钮（搭配非 inline 使用） */
  ghost: { type: Boolean, default: false },
})

function open() {
  if (!props.url) {
    uni.showToast({ title: '链接暂未配置', icon: 'none' })
    return
  }
  // #ifdef H5
  window.open(props.url, '_blank')
  // #endif
  // #ifndef H5
  uni.setClipboardData({
    data: props.url,
    success: () => {
      uni.showToast({ title: '链接已复制，请在浏览器打开', icon: 'none' })
    },
  })
  // #endif
}
</script>

<style scoped>
.ext-link--btn {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 88rpx;
  border-radius: 16rpx;
  background: #eef2ff;
  color: #4f46e5;
  font-size: 28rpx;
  font-weight: 600;
  padding: 0 32rpx;
}
.ext-link--btn.ext-link--ghost {
  background: rgba(255, 255, 255, 0.16);
  color: #ffffff;
  border: 2rpx solid rgba(255, 255, 255, 0.55);
}
.ext-link--inline {
  display: inline-flex;
  align-items: center;
  min-height: 56rpx;
  padding: 8rpx 20rpx;
  border-radius: 12rpx;
  background: #eef2ff;
  color: #4f46e5;
  font-size: 26rpx;
  font-weight: 500;
}
.ext-link--hover {
  background: #e0e7ff;
}
.ext-link__label {
  font-size: inherit;
}
.ext-link__arrow {
  margin-left: 6rpx;
  font-size: 28rpx;
  line-height: 1;
}
</style>
