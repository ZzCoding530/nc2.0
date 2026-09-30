<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Promotion, Refresh } from '@element-plus/icons-vue'
import { get, post, put } from '../utils/request'
import { beijingInputToUtc, utcToBeijingInput } from '../utils/format'

interface Cohort {
  id: number
  name: string
}

interface StudentOption {
  id: number
  name: string
  cohort?: string
}

interface LessonCard {
  id?: number
  code: string
  title: string
  lesson_type: string
  module_code: string
}

interface ScheduleRow {
  id: number
  lesson_code?: string
  lesson_card?: { code?: string }
  lesson?: { code?: string }
  scheduled_at?: string | null
  meeting_link?: string | null
  status?: string
}

interface MergedRow {
  code: string
  title: string
  lessonType: string
  moduleCode: string
  cardId: number | null
  scheduleId: number | null
  scheduledAt: string | null
  meetingLink: string
  status: string
  dirty: boolean
  saving: boolean
  sending: boolean
}

const STATUS_OPTIONS = [
  { value: 'planned', label: '未排' },
  { value: 'scheduled', label: '已排' },
  { value: 'done', label: '已完' },
  { value: 'skipped', label: '跳过' },
]

type TagType = 'primary' | 'info' | 'warning'

const LESSON_TYPE_TAG: Record<string, { label: string; type: TagType }> = {
  '1v1': { label: '1v1', type: 'primary' },
  recorded: { label: '录播', type: 'info' },
  validation: { label: '验收', type: 'warning' },
}

const EMAIL_TRIGGER_TEXT: Record<string, string> = {
  schedule_confirm: '排课确认邮件',
  schedule_change: '上课时间变更邮件',
}

const cohorts = ref<Cohort[]>([])
const students = ref<StudentOption[]>([])
const cards = ref<LessonCard[]>([])
const rows = ref<MergedRow[]>([])

const cohortId = ref<number | null>(null)
const studentId = ref<number | null>(null)

const studentsLoading = ref(false)
const schedulesLoading = ref(false)

const summary = computed(() => {
  let scheduled = 0
  let done = 0
  let skipped = 0
  for (const r of rows.value) {
    if (r.status === 'scheduled') scheduled += 1
    else if (r.status === 'done') done += 1
    else if (r.status === 'skipped') skipped += 1
  }
  const totalRows = rows.value.length
  return {
    total: totalRows,
    scheduled,
    done,
    skipped,
    planned: totalRows - scheduled - done - skipped,
  }
})

function scheduleLessonCode(row: ScheduleRow): string {
  return row.lesson_code ?? row.lesson_card?.code ?? row.lesson?.code ?? ''
}

function buildRows(schedules: ScheduleRow[], preserveDirty = false): MergedRow[] {
  const map = new Map<string, ScheduleRow>()
  for (const s of schedules) {
    const code = scheduleLessonCode(s)
    if (code) map.set(code, s)
  }
  const prev = new Map(rows.value.map((r) => [r.code, r]))
  const ordered = [...cards.value].sort(
    (a, b) =>
      a.module_code.localeCompare(b.module_code) || a.code.localeCompare(b.code),
  )
  return ordered.map((c) => {
    const s = map.get(c.code)
    const row: MergedRow = {
      code: c.code,
      title: c.title,
      lessonType: c.lesson_type,
      moduleCode: c.module_code,
      cardId: c.id ?? null,
      scheduleId: s?.id ?? null,
      scheduledAt: s?.scheduled_at ? utcToBeijingInput(s.scheduled_at) : '',
      meetingLink: s?.meeting_link ?? '',
      status: s?.status ?? 'planned',
      dirty: false,
      saving: false,
      sending: false,
    }
    // 保存某一行后刷新整表时，保留其他行尚未保存的编辑
    const p = prev.get(c.code)
    if (preserveDirty && p?.dirty) {
      row.scheduledAt = p.scheduledAt
      row.meetingLink = p.meetingLink
      row.status = p.status
      row.dirty = true
    }
    return row
  })
}

async function loadCohorts(): Promise<void> {
  try {
    const res = await get<{ items?: Cohort[] }>('/admin/cohorts')
    cohorts.value = res.items ?? []
  } catch {
    // 错误已由统一拦截器提示
  }
}

async function loadCards(): Promise<void> {
  try {
    const res = await get<{ items?: LessonCard[] }>('/admin/lesson-cards')
    cards.value = res.items ?? []
    rows.value = buildRows([])
  } catch {
    // 错误已由统一拦截器提示
  }
}

async function loadStudents(): Promise<void> {
  studentsLoading.value = true
  try {
    const params: Record<string, unknown> = { page: 1, page_size: 100 }
    if (cohortId.value) params.cohort_id = cohortId.value
    const res = await get<{ items?: StudentOption[] }>('/admin/students', params)
    students.value = res.items ?? []
  } catch {
    // 错误已由统一拦截器提示
  } finally {
    studentsLoading.value = false
  }
}

async function loadSchedules(preserveDirty = false): Promise<void> {
  if (!studentId.value) {
    rows.value = buildRows([])
    return
  }
  schedulesLoading.value = true
  try {
    const res = await get<{ items?: ScheduleRow[] } | ScheduleRow[]>('/admin/schedules', {
      student_id: studentId.value,
    })
    const list = Array.isArray(res) ? res : (res.items ?? [])
    rows.value = buildRows(list, preserveDirty)
  } catch {
    // 错误已由统一拦截器提示
  } finally {
    schedulesLoading.value = false
  }
}

function onCohortChange(): void {
  studentId.value = null
  students.value = []
  rows.value = buildRows([])
  loadStudents()
}

function onStudentChange(): void {
  loadSchedules(false)
}

async function saveRow(row: MergedRow): Promise<void> {
  if (!studentId.value) {
    ElMessage.warning('请先选择学员')
    return
  }
  row.saving = true
  try {
    const payload: Record<string, unknown> = {
      scheduled_at: beijingInputToUtc(row.scheduledAt),
      meeting_link: row.meetingLink.trim(),
      status: row.status,
    }
    let res: { email_triggered?: string | null } | undefined
    if (row.scheduleId) {
      res = await put<{ email_triggered?: string | null }>(
        `/admin/schedules/${row.scheduleId}`,
        payload,
      )
    } else {
      payload.student_id = studentId.value
      payload.lesson_code = row.code
      if (row.cardId !== null) payload.lesson_card_id = row.cardId
      res = await post<{ email_triggered?: string | null }>('/admin/schedules', payload)
    }
    const triggered = res?.email_triggered
    if (triggered && EMAIL_TRIGGER_TEXT[triggered]) {
      ElMessage.success(`「${row.code}」已保存，已触发${EMAIL_TRIGGER_TEXT[triggered]}`)
    } else {
      ElMessage.success(`「${row.code}」已保存（未触发邮件）`)
    }
    row.dirty = false
    // 重新拉取排期，同步新创建记录的 id
    await loadSchedules(true)
  } catch {
    // 错误已由统一拦截器提示
  } finally {
    row.saving = false
  }
}

async function sendPreviewReminder(row: MergedRow): Promise<void> {
  if (!row.scheduleId) return
  row.sending = true
  try {
    await post(`/admin/schedules/${row.scheduleId}/send-reminder`, {
      mail_type: 'preview_reminder',
    })
    ElMessage.success(`「${row.code}」预习提醒邮件已加入发送队列`)
  } catch {
    // 失败原因（如 LINK_REQUIRED：上课链接为空）已由统一拦截器提示
  } finally {
    row.sending = false
  }
}

onMounted(() => {
  loadCohorts()
  loadCards()
  loadStudents()
})
</script>

<template>
  <div class="page">
    <el-card shadow="never" class="filter-card">
      <div class="filter-bar">
        <div class="filter-item">
          <span class="filter-label">班期</span>
          <el-select
            v-model="cohortId"
            clearable
            placeholder="全部班期"
            style="width: 200px"
            @change="onCohortChange"
          >
            <el-option v-for="c in cohorts" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </div>
        <div class="filter-item">
          <span class="filter-label">学员</span>
          <el-select
            v-model="studentId"
            filterable
            clearable
            :loading="studentsLoading"
            placeholder="请选择学员"
            style="width: 240px"
            @change="onStudentChange"
          >
            <el-option
              v-for="s in students"
              :key="s.id"
              :label="s.name + (s.cohort ? `（${s.cohort}）` : '')"
              :value="s.id"
            />
          </el-select>
        </div>
        <el-button v-if="studentId" :icon="Refresh" @click="loadSchedules(false)">
          刷新排期
        </el-button>
        <div class="filter-spacer" />
        <div v-if="studentId" class="summary">
          共 {{ summary.total }} 课时 · 已排 {{ summary.scheduled }} · 已完
          {{ summary.done }} · 跳过 {{ summary.skipped }} · 未排 {{ summary.planned }}
        </div>
      </div>
    </el-card>

    <el-card shadow="never">
      <el-alert
        v-if="!studentId"
        type="info"
        :closable="false"
        show-icon
        title="请先选择班期与学员"
        description="选择学员后，在下方表格中逐课时填写排期时间、上课链接与状态；保存后系统将自动触发排课确认 / 时间变更邮件。"
      />
      <template v-else>
        <el-table
          v-loading="schedulesLoading"
          :data="rows"
          row-key="code"
          stripe
          size="small"
          :max-height="640"
        >
          <el-table-column label="模块" width="64">
            <template #default="scope">
              <span class="mono module-code">{{ scope.row.moduleCode }}</span>
            </template>
          </el-table-column>
          <el-table-column label="课时代号" width="96">
            <template #default="scope">
              <span class="mono">{{ scope.row.code }}</span>
            </template>
          </el-table-column>
          <el-table-column
            prop="title"
            label="课时标题"
            min-width="180"
            show-overflow-tooltip
          />
          <el-table-column label="类型" width="76">
            <template #default="scope">
              <el-tag
                size="small"
                effect="plain"
                :type="LESSON_TYPE_TAG[scope.row.lessonType]?.type ?? 'info'"
              >
                {{ LESSON_TYPE_TAG[scope.row.lessonType]?.label ?? scope.row.lessonType }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="排期时间" width="232">
            <template #default="scope">
              <el-date-picker
                v-model="scope.row.scheduledAt"
                type="datetime"
                format="YYYY-MM-DD HH:mm"
                value-format="YYYY-MM-DDTHH:mm:ss"
                placeholder="选择上课时间"
                style="width: 204px"
                @change="scope.row.dirty = true"
              />
            </template>
          </el-table-column>
          <el-table-column label="上课链接" min-width="230">
            <template #default="scope">
              <el-input
                v-model="scope.row.meetingLink"
                placeholder="如 https://meeting.tencent.com/d/xxx"
                clearable
                @input="scope.row.dirty = true"
              />
            </template>
          </el-table-column>
          <el-table-column label="状态" width="104">
            <template #default="scope">
              <el-select v-model="scope.row.status" @change="scope.row.dirty = true">
                <el-option
                  v-for="s in STATUS_OPTIONS"
                  :key="s.value"
                  :label="s.label"
                  :value="s.value"
                />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="212" fixed="right">
            <template #default="scope">
              <el-button
                size="small"
                :type="scope.row.dirty ? 'primary' : 'default'"
                :loading="scope.row.saving"
                @click="saveRow(scope.row)"
              >
                保存
              </el-button>
              <el-tooltip
                content="发送预习提醒邮件（需已保存排期且填写上课链接）"
                placement="top"
              >
                <span class="reminder-wrap">
                  <el-button
                    size="small"
                    :icon="Promotion"
                    :disabled="!scope.row.scheduleId"
                    :loading="scope.row.sending"
                    @click="sendPreviewReminder(scope.row)"
                  >
                    发预习邮件
                  </el-button>
                </span>
              </el-tooltip>
            </template>
          </el-table-column>
        </el-table>
      </template>
    </el-card>
  </div>
</template>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.filter-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-label {
  color: #606266;
  font-size: 13px;
  white-space: nowrap;
}

.filter-spacer {
  flex: 1;
}

.summary {
  font-size: 13px;
  color: #606266;
  white-space: nowrap;
}

.module-code {
  color: #909399;
  font-size: 12px;
}

.reminder-wrap {
  margin-left: 8px;
}
</style>
