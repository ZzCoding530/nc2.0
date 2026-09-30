<template>
  <view class="page-pad safe-bottom lesson-page">
    <!-- 骨架屏 -->
    <view v-if="loading" class="card">
      <view class="sk-row skeleton" style="width: 50%; height: 40rpx;"></view>
      <view class="sk-row skeleton" style="width: 100%; height: 120rpx; margin-top: 28rpx;"></view>
      <view class="sk-row skeleton" style="width: 100%; height: 200rpx; margin-top: 16rpx;"></view>
      <view class="sk-row skeleton" style="width: 100%; height: 120rpx; margin-top: 16rpx;"></view>
    </view>

    <template v-else-if="lesson">
      <!-- 顶部：返回 + 代号 chip + 状态 chip -->
      <view class="lesson-top">
        <view class="lesson-top__back" @click="goBack">
          <text>‹ 课表</text>
        </view>
        <view class="lesson-top__chips">
          <text class="chip chip-mono">{{ lesson.code }}</text>
          <text class="chip" :class="statusChip.cls">{{ statusChip.text }}</text>
        </view>
      </view>
      <view class="lesson-title-block">
        <text class="lesson-title">{{ lesson.title }}</text>
        <text class="lesson-meta">{{ metaText }}</text>
      </view>

      <!-- 上课信息卡（1v1 有排期时） -->
      <view v-if="isLiveLesson" class="card class-card" :class="{ 'class-card--history': isHistory }">
        <template v-if="isHistory">
          <!-- 已上课：历史态，灰底，只展示实际上课日期 -->
          <text class="class-card__label">已上课</text>
          <text class="class-card__time">{{ classTimeText }}</text>
        </template>
        <template v-else-if="hasSchedule">
          <text class="class-card__label">上课时间（北京时间）</text>
          <text class="class-card__time">{{ classTimeText }}</text>
          <view class="class-card__btns">
            <ExternalLink
              v-if="lesson.schedule.meeting_link"
              :url="lesson.schedule.meeting_link"
              label="进入教室"
            />
            <view class="btn btn-plain class-card__ics" @click="addToCalendar">
              <text>加日历</text>
            </view>
          </view>
        </template>
        <template v-else>
          <text class="class-card__label">上课时间（北京时间）</text>
          <text class="class-card__time class-card__time--muted">待排期 · 班主任会邮件通知你</text>
        </template>
      </view>

      <!-- 录播信息卡 -->
      <view v-if="isRecordedLesson" class="card class-card">
        <text class="class-card__label">录播 · 随时观看</text>
        <text class="class-card__time">共 {{ recordedItems.length }} 讲 · 已完成 {{ recordedDoneCount }} 讲</text>
      </view>

      <!-- 三区 tab -->
      <view v-if="tabs.length" class="tabs">
        <view
          v-for="t in tabs"
          :key="t.key"
          class="tabs__item"
          :class="{ 'tabs__item--active': activeTab === t.key }"
          @click="activeTab = t.key"
        >
          <text>{{ t.label }}</text>
        </view>
      </view>

      <!-- 预习区 -->
      <view v-if="activeTab === 'preview'" class="card">
        <!-- 未解锁：锁定态 + 距解锁倒计时 -->
        <view v-if="!lesson.preview_unlocked" class="locked">
          <text class="locked__icon">🔒</text>
          <text class="locked__title">预习尚未解锁</text>
          <text class="locked__desc">{{ lockText }}</text>
        </view>
        <!-- 已解锁 -->
        <template v-else>
          <text class="card-title">课前预习</text>
          <text v-if="lesson.content_summary" class="preview-intro">{{ lesson.content_summary }}</text>
          <view v-if="lesson.preview">
            <text v-if="lesson.preview.intro" class="preview-intro">{{ lesson.preview.intro }}</text>
            <view v-if="questions.length" class="preview-questions">
              <text class="preview-questions__label">三问预写（上课前完成）</text>
              <view v-for="(q, i) in questions" :key="i" class="preview-questions__item">
                <text class="preview-questions__num mono">{{ i + 1 }}.</text>
                <text class="preview-questions__text">{{ q }}</text>
              </view>
            </view>
            <view v-if="keywords.length" class="preview-keywords">
              <text v-for="k in keywords" :key="k" class="chip chip-brand preview-keywords__chip">{{ k }}</text>
            </view>
          </view>
          <!-- 标记为已读：点击后禁用变「已读」 -->
          <view
            class="btn btn-primary btn-block preview-read-btn"
            :class="{ disabled: previewRead }"
            @click="markRead"
          >
            <text>{{ previewRead ? '✓ 已读' : markingRead ? '提交中…' : '标记为已读' }}</text>
          </view>
        </template>
      </view>

      <!-- 录播逐讲区 -->
      <view v-if="activeTab === 'recorded'" class="card">
        <text class="card-title">逐讲清单</text>
        <view v-for="item in recordedItems" :key="item.code" class="rec-item">
          <view class="rec-item__texts" @click="noop">
            <text class="rec-item__title">{{ item.code }} · {{ item.title }}</text>
            <text class="rec-item__sub">时长 {{ item.duration }} 分钟</text>
          </view>
          <view class="rec-item__actions">
            <ExternalLink v-if="item.video_url" inline :url="item.video_url" label="看视频" />
            <view
              class="done-switch"
              :class="{ 'done-switch--on': item.done }"
              @click="toggleRecordedDone(item)"
            >
              <view class="done-switch__dot"></view>
            </view>
          </view>
        </view>
        <!-- 代码包外链 -->
        <view v-if="lesson.code_url" class="code-url-row">
          <text class="code-url-row__label">课程代码包</text>
          <ExternalLink inline :url="lesson.code_url" label="下载/查看" />
        </view>
      </view>

      <!-- 资料区 -->
      <view v-if="activeTab === 'material'" class="card">
        <text class="card-title">学习资料</text>
        <view v-if="materials.length === 0" class="empty-tip">
          <text>本课时暂无资料</text>
        </view>
        <view v-for="mat in materials" :key="mat.id" class="mat-item">
          <view class="mat-item__texts">
            <text class="mat-item__title">{{ mat.title }}</text>
            <view class="mat-item__tags">
              <text class="chip">{{ matTypeCN(mat.mat_type) }}</text>
              <text v-if="mat.required" class="chip chip-brand">必发</text>
            </view>
          </view>
          <ExternalLink inline :url="mat.url" label="打开" />
        </view>
        <text class="note">资料统一外部链接，更新即时生效</text>
      </view>

      <!-- 作业区 -->
      <view v-if="activeTab === 'homework'" class="card">
        <text class="card-title">课后作业</text>
        <view v-if="lesson.homework_def" class="hw-card">
          <text class="hw-card__label">作业要求</text>
          <text class="hw-card__def">{{ lesson.homework_def }}</text>
        </view>
        <view v-else class="empty-tip">
          <text>本课时暂无作业</text>
        </view>
        <text class="note">{{ lesson.homework_note || 'V1 作业通过邮件提交，面评时讲解' }}</text>
      </view>
    </template>
  </view>
</template>

<script setup>
import { ref, computed } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { get, post } from '../../utils/request'
import {
  toBeijingTime,
  weekdayCN,
  countdownText,
  toICSStamp,
  nowICSStamp,
  plusMinutes,
} from '../../utils/format'
import ExternalLink from '../../components/ExternalLink.vue'

const loading = ref(true)
const lessonCode = ref('')
const lesson = ref(null)
const activeTab = ref('preview')
const previewRead = ref(false)
const markingRead = ref(false)

const isLiveLesson = computed(() => lesson.value && lesson.value.type !== 'recorded')
const isRecordedLesson = computed(() => lesson.value && lesson.value.type === 'recorded')
const hasSchedule = computed(() => lesson.value && lesson.value.schedule && lesson.value.schedule.scheduled_at)
const isHistory = computed(
  () => lesson.value && lesson.value.schedule && lesson.value.schedule.status === 'done'
)
const questions = computed(() => (lesson.value && lesson.value.preview && lesson.value.preview.questions) || [])
const keywords = computed(() => (lesson.value && lesson.value.preview && lesson.value.preview.keywords) || [])
const materials = computed(() => (lesson.value && lesson.value.materials) || [])
const recordedItems = computed(() => (lesson.value && lesson.value.recorded_items) || [])
const recordedDoneCount = computed(() => recordedItems.value.filter((i) => i.done).length)

const classTimeText = computed(() => {
  if (!lesson.value || !hasSchedule.value) return ''
  const at = lesson.value.schedule.scheduled_at
  return `${toBeijingTime(at)}（${weekdayCN(at)}）`
})

const metaText = computed(() => {
  const l = lesson.value
  if (!l) return ''
  const parts = []
  if (l.module_title) parts.push(l.module_title)
  if (l.duration_min) parts.push(`${l.duration_min} 分钟`)
  if (l.effort_note) parts.push(l.effort_note)
  return parts.join(' · ')
})

/** 状态 chip */
const statusChip = computed(() => {
  const l = lesson.value
  if (!l) return { text: '', cls: '' }
  if (l.schedule && l.schedule.status === 'done') return { text: '已完成', cls: 'chip-green' }
  if (l.preview_unlocked) return { text: '预习期', cls: 'chip-brand' }
  if (l.schedule && l.schedule.status === 'scheduled') return { text: '已排课', cls: '' }
  return { text: '待排期', cls: '' }
})

/** 三区 tab：预习 / 逐讲（录播）/ 资料 / 作业 */
const tabs = computed(() => {
  const l = lesson.value
  if (!l) return []
  const list = []
  const showPreview = l.preview_unlocked || (l.preview && (l.preview.intro || l.preview.questions)) || (l.schedule && l.schedule.scheduled_at)
  if (showPreview) list.push({ key: 'preview', label: '预习' })
  if (isRecordedLesson.value && recordedItems.value.length) list.push({ key: 'recorded', label: '逐讲' })
  if (materials.value.length) list.push({ key: 'material', label: '资料' })
  if (l.homework_def) list.push({ key: 'homework', label: '作业' })
  return list
})

/** 预习锁定态倒计时文案（预习在 T-2 解锁） */
const lockText = computed(() => {
  const l = lesson.value
  if (!l) return ''
  if (!hasSchedule.value) return '开班排期后 2 天解锁预习内容，请留意班主任邮件。'
  const unlockAt = new Date(new Date(l.schedule.scheduled_at).getTime() - 48 * 3600 * 1000).toISOString()
  const cd = countdownText(unlockAt)
  return cd ? `预习将在上课前 2 天解锁（${cd}）` : '预习即将解锁，请稍后查看'
})

const MAT_TYPE_CN = {
  book: '书籍',
  doc: '文档',
  video: '视频',
  link: '链接',
  repo: '代码',
  slide: '讲义',
  paper: '论文',
}

function matTypeCN(t) {
  return MAT_TYPE_CN[t] || '资料'
}

function noop() {}

async function fetchLesson() {
  loading.value = true
  try {
    const res = await get(`/lessons/${encodeURIComponent(lessonCode.value)}`, {}, { silent: false })
    lesson.value = res
    previewRead.value = !!res.preview_read
    // 初始 tab（来自 query，如首页「看预习」定位预习区）
    let target = initialTab
    const keys = tabs.value.map((t) => t.key)
    if (!target || keys.indexOf(target) < 0) {
      target = isRecordedLesson.value && recordedItems.value.length && !tabs.value.some((t) => t.key === 'preview')
        ? 'recorded'
        : keys[0] || 'preview'
    }
    activeTab.value = target
  } catch (err) {
    if (err && (err.code === 'NOT_FOUND' || err.statusCode === 404)) {
      uni.showToast({ title: '课时不存在', icon: 'none' })
      setTimeout(goBack, 800)
    }
  } finally {
    loading.value = false
  }
}

let initialTab = ''
onLoad((options) => {
  lessonCode.value = (options && options.code) || ''
  initialTab = (options && options.tab) || ''
  if (!lessonCode.value) {
    uni.showToast({ title: '缺少课时参数', icon: 'none' })
    setTimeout(goBack, 800)
    return
  }
  fetchLesson()
})

function goBack() {
  const pages = getCurrentPages()
  if (pages && pages.length > 1) {
    uni.navigateBack()
  } else {
    uni.switchTab({ url: '/pages/map/index' })
  }
}

/** 标记预习已读：POST activity 后禁用变「已读」 */
async function markRead() {
  if (previewRead.value || markingRead.value) return
  markingRead.value = true
  try {
    await post(
      `/lessons/${encodeURIComponent(lessonCode.value)}/activity`,
      { act_type: 'preview_read' },
      { silent: true }
    )
    previewRead.value = true
    uni.showToast({ title: '已完成预习', icon: 'success' })
  } catch (err) {
    uni.showToast({ title: (err && err.message) || '标记失败，请重试', icon: 'none' })
  } finally {
    markingRead.value = false
  }
}

/** 录播逐讲完成开关：乐观更新，失败回滚 + toast */
async function toggleRecordedDone(item) {
  if (item.done) return // 已完成态不再重复标记（V1 仅支持标记，不支持取消）
  const prev = item.done
  item.done = true // 乐观
  try {
    await post(
      `/lessons/${encodeURIComponent(item.code)}/activity`,
      { act_type: 'recorded_done' },
      { silent: true }
    )
  } catch (err) {
    item.done = prev // 回滚
    uni.showToast({ title: (err && err.message) || '标记失败', icon: 'none' })
  }
}

/** 加日历：生成 .ics 下载（H5 用 a[download]，其他端复制 ICS 文本） */
function addToCalendar() {
  const l = lesson.value
  if (!l || !l.schedule || !l.schedule.scheduled_at) return
  const start = l.schedule.scheduled_at
  const end = plusMinutes(start, l.duration_min || 100)
  const lines = [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    'PRODID:-//NiceOffer//Student Center//CN',
    'CALSCALE:GREGORIAN',
    'METHOD:PUBLISH',
    'BEGIN:VEVENT',
    `UID:${l.code}-${Date.now()}@niceoffer`,
    `DTSTAMP:${nowICSStamp()}`,
    `DTSTART:${toICSStamp(start)}`,
    `DTEND:${toICSStamp(end)}`,
    `SUMMARY:${l.code} ${l.title} · NiceOffer`,
    `DESCRIPTION:上课链接：${l.schedule.meeting_link || '见邮件通知'}`,
    `LOCATION:${l.schedule.meeting_link || ''}`,
    'END:VEVENT',
    'END:VCALENDAR',
  ]
  const ics = lines.join('\r\n')
  // #ifdef H5
  const blob = new Blob([ics], { type: 'text/calendar;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `niceoffer-${l.code}.ics`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  setTimeout(() => {
    URL.revokeObjectURL(url)
  }, 1200)
  // #endif
  // #ifndef H5
  uni.setClipboardData({
    data: ics,
    success: () => {
      uni.showToast({ title: '日历内容已复制，可粘贴到日历应用', icon: 'none' })
    },
  })
  // #endif
}
</script>

<style scoped>
.lesson-page {
  padding-top: 16rpx;
}
.sk-row {
  margin-bottom: 8rpx;
}
.lesson-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.lesson-top__back {
  min-height: 88rpx;
  display: flex;
  align-items: center;
  font-size: 30rpx;
  color: #374151;
  padding-right: 24rpx;
}
.lesson-top__back:active {
  opacity: 0.6;
}
.lesson-top__chips {
  display: flex;
  align-items: center;
  gap: 12rpx;
}
.lesson-title-block {
  display: flex;
  flex-direction: column;
  padding: 8rpx 8rpx 24rpx;
}
.lesson-title {
  font-size: 38rpx;
  font-weight: 700;
  color: #111827;
}
.lesson-meta {
  margin-top: 8rpx;
  font-size: 24rpx;
  color: #9ca3af;
}
/* 上课信息卡（品牌浅底） */
.class-card {
  background: #eef2ff;
  border: 2rpx solid #e0e7ff;
}
.class-card--history {
  background: #f3f4f6;
  border-color: #e5e7eb;
}
.class-card__label {
  font-size: 24rpx;
  color: #4f46e5;
}
.class-card--history .class-card__label {
  color: #9ca3af;
}
.class-card__time {
  display: block;
  margin-top: 10rpx;
  font-size: 34rpx;
  font-weight: 700;
  color: #111827;
}
.class-card__time--muted {
  font-size: 28rpx;
  font-weight: 500;
  color: #6b7280;
}
.class-card__btns {
  display: flex;
  gap: 20rpx;
  margin-top: 28rpx;
}
.class-card__btns > view:first-child {
  flex: 1;
}
.class-card__ics {
  flex: 1;
}
/* 三区 tab */
.tabs {
  display: flex;
  background: #ffffff;
  border-radius: 16rpx;
  margin-bottom: 24rpx;
  overflow: hidden;
}
.tabs__item {
  flex: 1;
  min-height: 88rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28rpx;
  color: #6b7280;
  position: relative;
}
.tabs__item--active {
  color: #4f46e5;
  font-weight: 600;
}
.tabs__item--active::after {
  content: '';
  position: absolute;
  left: 50%;
  bottom: 8rpx;
  width: 48rpx;
  height: 6rpx;
  border-radius: 6rpx;
  background: #4f46e5;
  transform: translateX(-50%);
}
/* 预习 */
.preview-intro {
  display: block;
  margin-top: 20rpx;
  font-size: 28rpx;
  color: #374151;
  line-height: 1.8;
}
.preview-questions {
  margin-top: 32rpx;
}
.preview-questions__label {
  display: block;
  font-size: 28rpx;
  font-weight: 600;
  color: #111827;
  margin-bottom: 16rpx;
}
.preview-questions__item {
  display: flex;
  align-items: flex-start;
  margin-bottom: 20rpx;
}
.preview-questions__num {
  width: 48rpx;
  flex-shrink: 0;
  font-size: 28rpx;
  color: #4f46e5;
  font-weight: 600;
  line-height: 1.7;
}
.preview-questions__text {
  flex: 1;
  font-size: 28rpx;
  color: #374151;
  line-height: 1.7;
}
.preview-keywords {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
  margin-top: 28rpx;
}
.preview-keywords__chip {
  padding: 8rpx 24rpx;
}
.preview-read-btn {
  margin-top: 36rpx;
}
/* 锁定态 */
.locked {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 48rpx 16rpx;
}
.locked__icon {
  font-size: 64rpx;
}
.locked__title {
  margin-top: 24rpx;
  font-size: 32rpx;
  font-weight: 600;
  color: #111827;
}
.locked__desc {
  margin-top: 12rpx;
  font-size: 26rpx;
  color: #6b7280;
  text-align: center;
  line-height: 1.7;
}
/* 录播逐讲 */
.rec-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24rpx 0;
  border-bottom: 2rpx solid #f3f4f6;
}
.rec-item:last-of-type {
  border-bottom: none;
}
.rec-item__texts {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.rec-item__title {
  font-size: 28rpx;
  color: #111827;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rec-item__sub {
  margin-top: 6rpx;
  font-size: 24rpx;
  color: #9ca3af;
}
.rec-item__actions {
  display: flex;
  align-items: center;
  gap: 20rpx;
  margin-left: 16rpx;
  flex-shrink: 0;
}
/* 完成开关（热区含 padding ≥44px） */
.done-switch {
  width: 92rpx;
  height: 56rpx;
  border-radius: 999rpx;
  background: #e5e7eb;
  position: relative;
  transition: background 0.2s ease;
  box-sizing: border-box;
}
.done-switch__dot {
  position: absolute;
  top: 6rpx;
  left: 6rpx;
  width: 44rpx;
  height: 44rpx;
  border-radius: 999rpx;
  background: #ffffff;
  transition: transform 0.2s ease;
}
.done-switch--on {
  background: #16a34a;
}
.done-switch--on .done-switch__dot {
  transform: translateX(36rpx);
}
.code-url-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 28rpx;
  padding-top: 24rpx;
  border-top: 2rpx solid #f3f4f6;
}
.code-url-row__label {
  font-size: 28rpx;
  color: #374151;
}
/* 资料 */
.mat-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24rpx 0;
  border-bottom: 2rpx solid #f3f4f6;
}
.mat-item:last-of-type {
  border-bottom: none;
}
.mat-item__texts {
  flex: 1;
  min-width: 0;
  margin-right: 16rpx;
  display: flex;
  flex-direction: column;
}
.mat-item__title {
  font-size: 28rpx;
  color: #111827;
  line-height: 1.5;
}
.mat-item__tags {
  display: flex;
  gap: 12rpx;
  margin-top: 10rpx;
}
/* 作业 */
.hw-card {
  margin-top: 20rpx;
  background: #f9fafb;
  border: 2rpx solid #f3f4f6;
  border-radius: 16rpx;
  padding: 28rpx;
}
.hw-card__label {
  display: block;
  font-size: 24rpx;
  color: #9ca3af;
}
.hw-card__def {
  display: block;
  margin-top: 12rpx;
  font-size: 28rpx;
  color: #111827;
  line-height: 1.7;
}
.empty-tip {
  padding: 40rpx 0;
  text-align: center;
  font-size: 26rpx;
  color: #9ca3af;
}
</style>
