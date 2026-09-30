<template>
  <view class="page-pad safe-bottom">
    <!-- 骨架屏 -->
    <view v-if="loading" class="card">
      <view class="sk-row skeleton" style="width: 50%; height: 40rpx;"></view>
      <view class="sk-row skeleton" style="width: 100%; height: 88rpx; margin-top: 28rpx;"></view>
      <view class="sk-row skeleton" style="width: 100%; height: 88rpx; margin-top: 16rpx;"></view>
      <view class="sk-row skeleton" style="width: 100%; height: 88rpx; margin-top: 16rpx;"></view>
      <view class="sk-row skeleton" style="width: 60%; height: 88rpx; margin-top: 16rpx;"></view>
    </view>

    <template v-else>
      <!-- 模块折叠列表 -->
      <view v-for="mod in modules" :key="mod.code" class="card module-card">
        <!-- 模块头 -->
        <view class="module-head" @click="toggleModule(mod.code)">
          <view class="module-head__texts">
            <view class="module-head__title-row">
              <text class="module-head__code mono">{{ mod.code }}</text>
              <text class="module-head__title">{{ mod.title }}</text>
            </view>
            <text class="module-head__subtitle">{{ mod.subtitle }}</text>
          </view>
          <text class="module-head__arrow" :class="{ 'module-head__arrow--open': !isCollapsed(mod.code) }">›</text>
        </view>

        <!-- 课时行 / 录播组行 -->
        <view v-if="!isCollapsed(mod.code)" class="module-body">
          <view v-for="row in mod.rows" :key="row.key">
            <!-- 录播组行（part_group 折叠） -->
            <view v-if="row.type === 'group'" class="lesson-row" @click="goLesson(row.items[0].code)">
              <text class="lesson-row__code mono">{{ row.items[0].code }}–{{ row.items[row.items.length - 1].code }}</text>
              <view class="lesson-row__mid">
                <text class="lesson-row__title">录播 · {{ row.partGroup }}</text>
                <text class="lesson-row__sub">共 {{ row.total }} 讲 · 已看 {{ row.done }}/{{ row.total }}</text>
              </view>
              <text v-if="row.done >= row.total" class="lesson-row__mark lesson-row__mark--done">✓</text>
              <text v-else class="lesson-row__mark lesson-row__mark--partial">{{ row.done }}/{{ row.total }}</text>
            </view>

            <!-- 普通课时行 -->
            <view
              v-else
              class="lesson-row"
              :class="{ 'lesson-row--now': row.lesson.is_current }"
              @click="goLesson(row.lesson.code)"
            >
              <text class="lesson-row__code mono">{{ row.lesson.code }}</text>
              <view class="lesson-row__mid">
                <view class="lesson-row__title-wrap">
                  <text class="lesson-row__title">{{ row.lesson.title }}</text>
                  <text v-if="row.lesson.is_current" class="now-chip">NOW</text>
                </view>
                <text class="lesson-row__sub">{{ statusText(row.lesson) }}</text>
              </view>
              <text class="lesson-row__mark" :class="markClass(row.lesson)">{{ markSymbol(row.lesson) }}</text>
            </view>
          </view>
        </view>
      </view>

      <!-- FLEX 答疑模块卡（班主任联系方式） -->
      <view class="card qa-card">
        <view class="qa-card__head">
          <text class="qa-card__code mono">FLEX</text>
          <text class="qa-card__title">答疑课</text>
        </view>
        <text class="qa-card__contact">班主任联系方式：{{ qaContact || '待班主任配置' }}</text>
        <text class="qa-card__note">有问题随时邮件班主任预约答疑，1v1 课后也可直接提问。</text>
      </view>
    </template>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { get } from '../../utils/request'
import { toBeijingTime } from '../../utils/format'

const loading = ref(true)
const modules = ref([])
const qaContact = ref('')
const collapsed = ref({})

const COLLAPSE_KEY = 'niceoffer_map_collapse'

/** 课时行三列的状态副行文案 */
function statusText(lesson) {
  const s = lesson.display_status
  if (s === 'done') {
    return lesson.scheduled_at ? `已完成 · ${toBeijingTime(lesson.scheduled_at)}` : '已完成'
  }
  if (s === 'preview') {
    return lesson.scheduled_at ? `预习已发 · ${toBeijingTime(lesson.scheduled_at)} 上课` : '预习已发'
  }
  if (s === 'ready') {
    return lesson.scheduled_at ? `${toBeijingTime(lesson.scheduled_at)} 上课` : '已排课'
  }
  if (s === 'locked') return '未解锁'
  return '待排期'
}

/** 右侧状态符：✓=done 绿、›=preview/ready、·=pending 灰 */
function markSymbol(lesson) {
  const s = lesson.display_status
  if (s === 'done') return '✓'
  if (s === 'preview') return '›'
  if (s === 'ready') return '›'
  return '·'
}

function markClass(lesson) {
  const s = lesson.display_status
  if (s === 'done') return 'lesson-row__mark--done'
  if (s === 'preview') return 'lesson-row__mark--preview'
  if (s === 'ready') return 'lesson-row__mark--ready'
  return 'lesson-row__mark--pending'
}

/** 模块 lessons → 展示行（录播按 part_group 折叠成组行） */
function buildRows(lessons) {
  const rows = []
  const groupMap = {}
  ;(lessons || []).forEach((l, i) => {
    if (l.type === 'recorded' && l.part_group) {
      if (!groupMap[l.part_group]) {
        const row = {
          key: `grp-${l.part_group}`,
          type: 'group',
          partGroup: l.part_group,
          items: [],
          done: 0,
          total: 0,
        }
        groupMap[l.part_group] = row
        rows.push(row)
      }
      const g = groupMap[l.part_group]
      g.items.push(l)
      g.total += 1
      if (l.display_status === 'done') g.done += 1
    } else {
      rows.push({ key: `ls-${l.code}-${i}`, type: 'lesson', lesson: l })
    }
  })
  return rows
}

function loadCollapse() {
  try {
    const raw = uni.getStorageSync(COLLAPSE_KEY)
    if (raw) collapsed.value = typeof raw === 'string' ? JSON.parse(raw) : raw
  } catch (e) {
    collapsed.value = {}
  }
}

function isCollapsed(code) {
  return !!collapsed.value[code]
}

function toggleModule(code) {
  const next = { ...collapsed.value }
  if (next[code]) {
    delete next[code]
  } else {
    next[code] = true
  }
  collapsed.value = next
  try {
    uni.setStorageSync(COLLAPSE_KEY, JSON.stringify(next))
  } catch (e) {
    // 存储失败不影响交互
  }
}

async function fetchMap() {
  loading.value = true
  try {
    const res = await get('/map')
    modules.value = (res.modules || []).map((m) => ({ ...m, rows: buildRows(m.lessons) }))
  } finally {
    loading.value = false
  }
}

async function fetchQaContact() {
  try {
    const res = await get('/me', {}, { silent: true })
    qaContact.value = (res && res.links && res.links.qa_contact) || ''
  } catch (e) {
    // 静默降级
  }
}

onLoad(() => {
  loadCollapse()
  fetchMap()
  fetchQaContact()
})

function goLesson(code) {
  if (!code) return
  uni.navigateTo({ url: `/pages/lesson/index?code=${encodeURIComponent(code)}` })
}
</script>

<style scoped>
.sk-row {
  margin-bottom: 8rpx;
}
.module-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 88rpx;
}
.module-head__texts {
  flex: 1;
}
.module-head__title-row {
  display: flex;
  align-items: center;
}
.module-head__code {
  font-size: 24rpx;
  color: #4f46e5;
  background: #eef2ff;
  padding: 2rpx 14rpx;
  border-radius: 8rpx;
  margin-right: 16rpx;
}
.module-head__title {
  font-size: 32rpx;
  font-weight: 700;
  color: #111827;
}
.module-head__subtitle {
  display: block;
  margin-top: 8rpx;
  font-size: 24rpx;
  color: #9ca3af;
}
.module-head__arrow {
  font-size: 36rpx;
  color: #9ca3af;
  transform: rotate(90deg);
  transition: transform 0.2s ease;
}
.module-head__arrow--open {
  transform: rotate(-90deg);
}
.module-body {
  margin-top: 8rpx;
}
.lesson-row {
  display: flex;
  align-items: center;
  padding: 24rpx 16rpx;
  border-bottom: 2rpx solid #f3f4f6;
  border-radius: 12rpx;
  min-height: 88rpx;
  box-sizing: border-box;
}
.lesson-row:last-child {
  border-bottom: none;
}
.lesson-row:active {
  background: #f9fafb;
}
/* 当前 NOW 课：品牌色高亮 */
.lesson-row--now {
  background: #eef2ff;
  border-bottom-color: #e0e7ff;
}
.lesson-row__code {
  width: 108rpx;
  font-size: 26rpx;
  color: #4f46e5;
  font-weight: 600;
  flex-shrink: 0;
}
.lesson-row--now .lesson-row__code {
  color: #4338ca;
}
.lesson-row__mid {
  flex: 1;
  min-width: 0;
}
.lesson-row__title-wrap {
  display: flex;
  align-items: center;
}
.lesson-row__title {
  font-size: 28rpx;
  color: #111827;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.now-chip {
  margin-left: 12rpx;
  flex-shrink: 0;
  font-size: 20rpx;
  font-weight: 700;
  color: #ffffff;
  background: #4f46e5;
  border-radius: 8rpx;
  padding: 2rpx 12rpx;
  letter-spacing: 2rpx;
}
.lesson-row__sub {
  display: block;
  margin-top: 6rpx;
  font-size: 24rpx;
  color: #9ca3af;
}
.lesson-row__mark {
  flex-shrink: 0;
  margin-left: 16rpx;
  font-size: 32rpx;
  font-weight: 600;
}
.lesson-row__mark--done {
  color: #16a34a;
}
.lesson-row__mark--preview {
  color: #4f46e5;
}
.lesson-row__mark--ready {
  color: #9ca3af;
}
.lesson-row__mark--pending {
  color: #d1d5db;
}
.lesson-row__mark--partial {
  font-size: 24rpx;
  color: #4f46e5;
  font-weight: 600;
}
.qa-card__head {
  display: flex;
  align-items: center;
}
.qa-card__code {
  font-size: 24rpx;
  color: #16a34a;
  background: #f0fdf4;
  padding: 2rpx 14rpx;
  border-radius: 8rpx;
  margin-right: 16rpx;
}
.qa-card__title {
  font-size: 30rpx;
  font-weight: 600;
  color: #111827;
}
.qa-card__contact {
  display: block;
  margin-top: 20rpx;
  font-size: 28rpx;
  color: #374151;
  word-break: break-all;
}
.qa-card__note {
  display: block;
  margin-top: 12rpx;
  font-size: 24rpx;
  color: #9ca3af;
  line-height: 1.6;
}
</style>
