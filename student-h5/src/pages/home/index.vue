<template>
  <view class="page-pad safe-bottom">
    <!-- 骨架屏 -->
    <view v-if="loading" class="card">
      <view class="sk-row skeleton" style="width: 40%; height: 40rpx;"></view>
      <view class="sk-row skeleton" style="width: 100%; height: 24rpx; margin-top: 28rpx;"></view>
      <view class="sk-row skeleton" style="width: 70%; height: 24rpx; margin-top: 16rpx;"></view>
      <view class="sk-row skeleton" style="width: 100%; height: 160rpx; margin-top: 32rpx;"></view>
    </view>

    <template v-else>
      <!-- 问候行：姓名 + 班期 chip -->
      <view class="greet-row">
        <text class="greet-row__name">{{ greeting }}，{{ student.name || '同学' }}</text>
        <text v-if="student.cohort" class="chip chip-brand">{{ student.cohort }}</text>
      </view>

      <!-- 进度卡：两条独立进度条 -->
      <view class="card">
        <text class="card-title">学习进度</text>
        <view class="progress-item">
          <view class="progress-item__head">
            <text class="progress-item__label">1v1 直播课</text>
            <text class="progress-item__num mono">{{ progress.one_on_one.done }}/{{ progress.one_on_one.total }}</text>
          </view>
          <view class="progress-bar">
            <view class="progress-bar__fill" :style="{ width: pct(progress.one_on_one) + '%' }"></view>
          </view>
        </view>
        <view class="progress-item">
          <view class="progress-item__head">
            <text class="progress-item__label">录播课</text>
            <text class="progress-item__num mono">{{ progress.recorded.done }}/{{ progress.recorded.total }}</text>
          </view>
          <view class="progress-bar">
            <view class="progress-bar__fill progress-bar__fill--green" :style="{ width: pct(progress.recorded) + '%' }"></view>
          </view>
        </view>
      </view>

      <!-- 下一节课卡（品牌色底） -->
      <view v-if="nextLesson" class="next-card">
        <view class="next-card__top">
          <text class="next-card__code mono">{{ nextLesson.code }}</text>
          <text v-if="isToday" class="next-card__today">今天</text>
        </view>
        <text class="next-card__title">{{ nextLesson.title }}</text>
        <text class="next-card__time">{{ lessonTimeText }}</text>
        <view class="next-card__btns">
          <view class="next-card__btn-preview" @click="goPreview">
            <text>看预习</text>
          </view>
          <ExternalLink
            v-if="nextLesson.meeting_link"
            class="next-card__btn-link"
            :class="{ 'next-card__btn-link--pulse': within30min }"
            ghost
            :url="nextLesson.meeting_link"
            label="上课链接"
          />
        </view>
        <text v-if="within30min" class="next-card__hint">临近开课，上课链接已就绪</text>
      </view>
      <!-- 无排期：占位卡 -->
      <view v-else class="card placeholder-card">
        <text class="placeholder-card__icon">📅</text>
        <text class="placeholder-card__text">待排期 · 班主任会邮件通知你</text>
      </view>

      <!-- 待办列表 -->
      <view class="card">
        <text class="card-title">待办</text>
        <view v-if="visibleTodos.length === 0" class="todo-empty">
          <text>暂无待办，保持节奏继续加油 💪</text>
        </view>
        <view v-for="todo in visibleTodos" :key="todo.key" class="todo-row">
          <view class="todo-row__main" @click="goTodo(todo)">
            <view class="todo-row__texts">
              <text class="todo-row__title">{{ todo.title }}</text>
              <text class="todo-row__sub">{{ todo.sub }}</text>
            </view>
          </view>
          <view class="todo-row__btn" :class="{ 'todo-row__btn--go': todo.btnGo }" @click="finishTodo(todo)">
            <text>{{ todo.btnLabel }}</text>
          </view>
        </view>
      </view>
    </template>
  </view>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { onLoad, onShow } from '@dcloudio/uni-app'
import { get, post } from '../../utils/request'
import { student, loadAuth, setAuth, token } from '../../store/user'
import { toBeijingTime, weekdayCN, isWithin30MinBefore } from '../../utils/format'
import ExternalLink from '../../components/ExternalLink.vue'

const loading = ref(true)
const loadedOnce = ref(false)
const progress = reactive({
  one_on_one: { done: 0, total: 0 },
  recorded: { done: 0, total: 0 },
})
const nextLesson = ref(null)
const within30min = ref(false)
const todos = ref([])

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '凌晨好'
  if (h < 12) return '早上好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
})

const lessonTimeText = computed(() => {
  if (!nextLesson.value || !nextLesson.value.scheduled_at) return ''
  return `${toBeijingTime(nextLesson.value.scheduled_at)}（${weekdayCN(nextLesson.value.scheduled_at)} · 北京时间）`
})

/** 是否今天上课（按北京时间） */
const isToday = computed(() => {
  if (!nextLesson.value || !nextLesson.value.scheduled_at) return false
  const bj = new Date(new Date(nextLesson.value.scheduled_at).getTime() + 8 * 3600 * 1000)
  const nowBJ = new Date(Date.now() + 8 * 3600 * 1000)
  return (
    bj.getUTCFullYear() === nowBJ.getUTCFullYear() &&
    bj.getUTCMonth() === nowBJ.getUTCMonth() &&
    bj.getUTCDate() === nowBJ.getUTCDate()
  )
})

const visibleTodos = computed(() => todos.value.filter((t) => !t.removed))

function pct(p) {
  if (!p || !p.total) return 0
  return Math.min(100, Math.round((p.done / p.total) * 100))
}

/** 接口 todos → 展示模型（preview 待办可标记完成；录播组待办引导去课表） */
function buildTodos(list) {
  return (list || [])
    .filter((t) => !t.acted)
    .map((t, i) => {
      if (t.kind === 'preview') {
        return {
          key: `preview-${t.lesson_code}-${i}`,
          kind: 'preview',
          lessonCode: t.lesson_code,
          title: t.title || '预习 · 三问预写',
          sub: `课时 ${t.lesson_code}`,
          btnLabel: '完成',
          btnGo: false,
          removed: false,
        }
      }
      const allDone = (t.done_count || 0) >= (t.total || 0)
      return {
        key: `recorded-${t.part_group}-${i}`,
        kind: 'recorded',
        partGroup: t.part_group,
        title: t.title || `录播 ${t.part_group}`,
        sub: `已看 ${t.done_count || 0}/${t.total || 0}`,
        doneCount: t.done_count || 0,
        total: t.total || 0,
        btnLabel: allDone ? '完成' : '去观看',
        btnGo: !allDone,
        removed: false,
      }
    })
}

async function fetchOverview() {
  loading.value = true
  try {
    const res = await get('/overview')
    if (res.progress) {
      progress.one_on_one = res.progress.one_on_one || { done: 0, total: 0 }
      progress.recorded = res.progress.recorded || { done: 0, total: 0 }
    }
    nextLesson.value = res.next_lesson && res.next_lesson.status !== null ? res.next_lesson : null
    within30min.value = nextLesson.value ? isWithin30MinBefore(nextLesson.value.scheduled_at) : false
    todos.value = buildTodos(res.todos)
  } finally {
    loading.value = false
    loadedOnce.value = true
  }
}

async function ensureStudentInfo() {
  if (student.value && student.value.name) return
  try {
    const res = await get('/me', {}, { silent: true })
    if (res && res.student && token.value) {
      setAuth(token.value, res.student)
    }
  } catch (e) {
    // 问候行降级为「同学」
  }
}

onLoad(() => {
  loadAuth()
  ensureStudentInfo()
  fetchOverview()
})

onShow(() => {
  // 从课时页返回时刷新（跳过首次，onLoad 已拉取）
  if (loadedOnce.value && !loading.value) {
    fetchOverview()
  }
})

function goPreview() {
  if (!nextLesson.value) return
  uni.navigateTo({
    url: `/pages/lesson/index?code=${encodeURIComponent(nextLesson.value.code)}&tab=preview`,
  })
}

function goTodo(todo) {
  if (todo.kind === 'preview') {
    uni.navigateTo({
      url: `/pages/lesson/index?code=${encodeURIComponent(todo.lessonCode)}&tab=preview`,
    })
  } else {
    // 录播组待办 → 课表页有分组清单与逐讲详情入口
    uni.switchTab({ url: '/pages/map/index' })
  }
}

/** 行内按钮点击即消失：乐观更新，失败回滚 + toast */
async function finishTodo(todo) {
  if (todo.removed) return
  // 录播组未看完：引导去课表继续观看，不做标记
  if (todo.kind === 'recorded' && todo.btnGo) {
    goTodo(todo)
    return
  }
  todo.removed = true // 乐观移除
  try {
    if (todo.kind === 'preview') {
      await post(
        `/lessons/${encodeURIComponent(todo.lessonCode)}/activity`,
        { act_type: 'preview_read' },
        { silent: true }
      )
    } else {
      // 录播组已全部看完：以后台数据复核（overview 幂等刷新确认）
      await get('/overview', {}, { silent: true })
    }
    uni.showToast({ title: '已完成', icon: 'success' })
  } catch (err) {
    todo.removed = false // 回滚
    uni.showToast({ title: (err && err.message) || '操作失败，已恢复', icon: 'none' })
  }
}
</script>

<style scoped>
.sk-row {
  margin-bottom: 8rpx;
}
.greet-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8rpx 8rpx 28rpx;
}
.greet-row__name {
  font-size: 36rpx;
  font-weight: 700;
  color: #111827;
}
.progress-item {
  margin-top: 28rpx;
}
.progress-item__head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 14rpx;
}
.progress-item__label {
  font-size: 28rpx;
  color: #374151;
}
.progress-item__num {
  font-size: 26rpx;
  color: #6b7280;
}
.progress-bar {
  height: 16rpx;
  background: #eef2ff;
  border-radius: 999rpx;
  overflow: hidden;
}
.progress-bar__fill {
  height: 100%;
  background: #4f46e5;
  border-radius: 999rpx;
  transition: width 0.4s ease;
}
.progress-bar__fill--green {
  background: #16a34a;
}
.next-card {
  background: linear-gradient(135deg, #4f46e5 0%, #6366f1 60%, #6d5ff0 100%);
  border-radius: 24rpx;
  padding: 36rpx 32rpx;
  margin-bottom: 24rpx;
  box-shadow: 0 8rpx 24rpx rgba(79, 70, 229, 0.25);
  display: flex;
  flex-direction: column;
}
.next-card__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.next-card__code {
  font-size: 26rpx;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.85);
  background: rgba(255, 255, 255, 0.16);
  padding: 4rpx 16rpx;
  border-radius: 8rpx;
}
.next-card__today {
  font-size: 24rpx;
  color: #4f46e5;
  background: #ffffff;
  padding: 4rpx 16rpx;
  border-radius: 999rpx;
  font-weight: 600;
}
.next-card__title {
  margin-top: 20rpx;
  font-size: 36rpx;
  font-weight: 700;
  color: #ffffff;
}
.next-card__time {
  margin-top: 12rpx;
  font-size: 26rpx;
  color: rgba(255, 255, 255, 0.85);
}
.next-card__btns {
  display: flex;
  gap: 20rpx;
  margin-top: 32rpx;
}
.next-card__btn-preview {
  flex: 1;
  min-height: 88rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 16rpx;
  background: #ffffff;
  color: #4f46e5;
  font-size: 28rpx;
  font-weight: 600;
}
.next-card__btn-preview:active {
  opacity: 0.85;
}
.next-card__btn-link {
  flex: 1;
}
/* 开课前 30 分钟：按钮呼吸高亮 */
.next-card__btn-link--pulse {
  animation: breathe 2s ease-in-out infinite;
}
@keyframes breathe {
  0%,
  100% {
    box-shadow: 0 0 0 0 rgba(255, 255, 255, 0.6);
    opacity: 1;
  }
  50% {
    box-shadow: 0 0 0 14rpx rgba(255, 255, 255, 0);
    opacity: 0.9;
  }
}
.next-card__hint {
  margin-top: 20rpx;
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.8);
}
.placeholder-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 56rpx 32rpx;
}
.placeholder-card__icon {
  font-size: 56rpx;
}
.placeholder-card__text {
  margin-top: 20rpx;
  font-size: 28rpx;
  color: #6b7280;
}
.todo-empty {
  padding: 32rpx 0 16rpx;
  font-size: 26rpx;
  color: #9ca3af;
  text-align: center;
}
.todo-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24rpx 0;
  border-bottom: 2rpx solid #f3f4f6;
}
.todo-row:last-child {
  border-bottom: none;
}
.todo-row__main {
  flex: 1;
  min-height: 72rpx;
  display: flex;
  align-items: center;
}
.todo-row__texts {
  display: flex;
  flex-direction: column;
}
.todo-row__title {
  font-size: 28rpx;
  color: #111827;
}
.todo-row__sub {
  margin-top: 4rpx;
  font-size: 24rpx;
  color: #9ca3af;
}
.todo-row__btn {
  min-height: 64rpx;
  padding: 0 28rpx;
  margin-left: 16rpx;
  border-radius: 999rpx;
  background: #f0fdf4;
  color: #16a34a;
  font-size: 26rpx;
  font-weight: 600;
  display: flex;
  align-items: center;
}
.todo-row__btn--go {
  background: #eef2ff;
  color: #4f46e5;
}
.todo-row__btn:active {
  opacity: 0.75;
}
</style>
