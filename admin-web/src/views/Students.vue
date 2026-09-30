<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'
import { get, post } from '../utils/request'
import { formatBeijing, formatRate } from '../utils/format'

interface StudentProgress {
  one_on_one_done?: number
  preview_read_rate?: number
  recorded_done?: number
}

interface Student {
  id: number
  name: string
  email_masked?: string
  cohort?: string
  status?: string
  progress?: StudentProgress
  last_login_at?: string | null
}

interface Cohort {
  id: number
  name: string
}

type StatusTagType = 'success' | 'warning' | 'danger' | 'info'

const STATUS_TAG: Record<string, { label: string; type: StatusTagType }> = {
  active: { label: '已激活', type: 'success' },
  pending: { label: '待激活', type: 'warning' },
  locked: { label: '已锁定', type: 'danger' },
  inactive: { label: '已停用', type: 'info' },
  disabled: { label: '已停用', type: 'info' },
}

const cohorts = ref<Cohort[]>([])
const students = ref<Student[]>([])
const total = ref(0)
const loading = ref(false)

const cohortId = ref<number | null>(null)
const stale = ref(false)
const page = ref(1)
const pageSize = ref(50)

const importVisible = ref(false)
const importLoading = ref(false)
const importEmails = ref('')
const importCohortId = ref<number | null>(null)

function buildQuery(): Record<string, unknown> {
  const params: Record<string, unknown> = {
    page: page.value,
    page_size: pageSize.value,
  }
  if (cohortId.value) params.cohort_id = cohortId.value
  if (stale.value) params.stale = 1
  return params
}

async function loadStudents(): Promise<void> {
  loading.value = true
  try {
    const res = await get<{ items?: Student[]; total?: number }>(
      '/admin/students',
      buildQuery(),
    )
    students.value = res.items ?? []
    total.value = res.total ?? 0
  } catch {
    // 错误已由统一拦截器提示
  } finally {
    loading.value = false
  }
}

async function loadCohorts(): Promise<void> {
  try {
    const res = await get<{ items?: Cohort[] }>('/admin/cohorts')
    cohorts.value = res.items ?? []
  } catch {
    // 错误已由统一拦截器提示
  }
}

function onFilterChange(): void {
  page.value = 1
  loadStudents()
}

function onPageChange(): void {
  loadStudents()
}

function openImport(): void {
  importEmails.value = ''
  importCohortId.value = cohortId.value
  importVisible.value = true
}

async function submitImport(): Promise<void> {
  if (!importCohortId.value) {
    ElMessage.warning('请选择导入班期')
    return
  }
  const emails = importEmails.value
    .split(/[\s,;，；]+/)
    .map((s) => s.trim())
    .filter((s) => s.length > 0)
  if (emails.length === 0) {
    ElMessage.warning('请粘贴至少一个邮箱')
    return
  }
  importLoading.value = true
  try {
    const res = await post<{ imported?: number; duplicated?: number }>(
      '/admin/students',
      { emails, cohort_id: importCohortId.value },
    )
    ElMessage.success(
      `导入完成：新增 ${res.imported ?? 0} 个，重复跳过 ${res.duplicated ?? 0} 个`,
    )
    importVisible.value = false
    page.value = 1
    loadStudents()
  } catch {
    // 错误已由统一拦截器提示
  } finally {
    importLoading.value = false
  }
}

onMounted(() => {
  loadCohorts()
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
            style="width: 180px"
            @change="onFilterChange"
          >
            <el-option v-for="c in cohorts" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </div>
        <div class="filter-item">
          <span class="filter-label">掉队筛选</span>
          <el-switch v-model="stale" active-text="7 天未登录" @change="onFilterChange" />
        </div>
        <div class="filter-spacer" />
        <el-button :icon="Refresh" @click="loadStudents">刷新</el-button>
        <el-button type="primary" :icon="Plus" @click="openImport">导入白名单</el-button>
      </div>
    </el-card>

    <el-card shadow="never">
      <el-table v-loading="loading" :data="students" stripe>
        <el-table-column prop="name" label="姓名" min-width="100" />
        <el-table-column prop="email_masked" label="邮箱（脱敏）" min-width="170" />
        <el-table-column prop="cohort" label="班期" min-width="110" />
        <el-table-column label="状态" width="90">
          <template #default="scope">
            <el-tag
              size="small"
              :type="STATUS_TAG[scope.row.status ?? '']?.type ?? 'info'"
            >
              {{ STATUS_TAG[scope.row.status ?? '']?.label ?? scope.row.status ?? '—' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="进度" min-width="190">
          <template #default="scope">
            <div class="progress-lines">
              <span>1v1 完成：{{ scope.row.progress?.one_on_one_done ?? 0 }}/15</span>
              <span>预习已读率：{{ formatRate(scope.row.progress?.preview_read_rate) }}</span>
              <span>录播观看：{{ scope.row.progress?.recorded_done ?? 0 }}/27</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="最后登录（北京时间）" min-width="150">
          <template #default="scope">
            {{ formatBeijing(scope.row.last_login_at) }}
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-bar">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @current-change="onPageChange"
          @size-change="onFilterChange"
        />
      </div>
    </el-card>

    <el-dialog v-model="importVisible" title="导入开班白名单" width="560px">
      <el-form label-width="80px">
        <el-form-item label="班期" required>
          <el-select
            v-model="importCohortId"
            placeholder="选择目标班期"
            style="width: 100%"
          >
            <el-option v-for="c in cohorts" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="邮箱列表" required>
          <el-input
            v-model="importEmails"
            type="textarea"
            :rows="8"
            placeholder="每行一个邮箱，支持逗号 / 分号分隔&#10;例如：&#10;student@example.com&#10;tom@example.com"
          />
        </el-form-item>
      </el-form>
      <div class="import-tip">
        提交后批量写入所选班期的白名单；已存在的邮箱会计入 duplicated，不会重复写入。
      </div>
      <template #footer>
        <el-button @click="importVisible = false">取消</el-button>
        <el-button type="primary" :loading="importLoading" @click="submitImport">
          开始导入
        </el-button>
      </template>
    </el-dialog>
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

.progress-lines {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 12px;
  color: #606266;
  line-height: 1.6;
}

.pagination-bar {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.import-tip {
  font-size: 12px;
  color: #909399;
  line-height: 1.6;
  margin-left: 80px;
}
</style>
