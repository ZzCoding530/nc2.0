<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { get, post } from '../utils/request'
import { formatBeijing } from '../utils/format'

interface EmailLog {
  id: number
  to_email_masked?: string
  mail_type: string
  lesson_code?: string | null
  status: string
  sent_at?: string | null
  retry_count?: number
}

const MAIL_TYPES = [
  { value: 'verify', label: '注册验证' },
  { value: 'reset', label: '密码重置' },
  { value: 'welcome', label: '开班欢迎' },
  { value: 'schedule_confirm', label: '排课确认' },
  { value: 'schedule_change', label: '时间变更' },
  { value: 'preview_reminder', label: '预习提醒' },
  { value: 'class_reminder', label: '上课提醒' },
]

type StatusTagType = 'success' | 'warning' | 'danger' | 'info'

const STATUS_META: Record<string, { label: string; type: StatusTagType }> = {
  pending: { label: '待发送', type: 'warning' },
  sent: { label: '已发送', type: 'success' },
  failed: { label: '发送失败', type: 'danger' },
}

const MAIL_TYPE_LABEL: Record<string, string> = Object.fromEntries(
  MAIL_TYPES.map((t) => [t.value, t.label]),
)

const logs = ref<EmailLog[]>([])
const total = ref(0)
const loading = ref(false)
const mailType = ref('')
const status = ref('')
const page = ref(1)
const pageSize = ref(20)
const retryingId = ref<number | null>(null)

async function loadLogs(): Promise<void> {
  loading.value = true
  try {
    const params: Record<string, unknown> = {
      page: page.value,
      page_size: pageSize.value,
    }
    if (mailType.value) params.mail_type = mailType.value
    if (status.value) params.status = status.value
    const res = await get<{ items?: EmailLog[]; total?: number }>('/admin/email-logs', params)
    logs.value = res.items ?? []
    total.value = res.total ?? 0
  } catch {
    // 错误已由统一拦截器提示
  } finally {
    loading.value = false
  }
}

function onFilterChange(): void {
  page.value = 1
  loadLogs()
}

function onPageChange(): void {
  loadLogs()
}

async function retry(row: EmailLog): Promise<void> {
  retryingId.value = row.id
  try {
    await post(`/admin/email-logs/${row.id}/retry`)
    ElMessage.success('已重新加入发送队列')
    loadLogs()
  } catch {
    // 错误已由统一拦截器提示
  } finally {
    retryingId.value = null
  }
}

onMounted(loadLogs)
</script>

<template>
  <div class="page">
    <el-card shadow="never" class="filter-card">
      <div class="filter-bar">
        <div class="filter-item">
          <span class="filter-label">邮件类型</span>
          <el-select
            v-model="mailType"
            clearable
            placeholder="全部类型"
            style="width: 160px"
            @change="onFilterChange"
          >
            <el-option v-for="t in MAIL_TYPES" :key="t.value" :label="t.label" :value="t.value" />
          </el-select>
        </div>
        <div class="filter-item">
          <span class="filter-label">状态</span>
          <el-select
            v-model="status"
            clearable
            placeholder="全部状态"
            style="width: 140px"
            @change="onFilterChange"
          >
            <el-option
              v-for="(meta, value) in STATUS_META"
              :key="value"
              :label="meta.label"
              :value="value"
            />
          </el-select>
        </div>
        <div class="filter-spacer" />
        <el-button :icon="Refresh" @click="loadLogs">刷新</el-button>
      </div>
    </el-card>

    <el-card shadow="never">
      <el-table v-loading="loading" :data="logs" stripe>
        <el-table-column label="类型" min-width="110">
          <template #default="scope">
            {{ MAIL_TYPE_LABEL[scope.row.mail_type] ?? scope.row.mail_type }}
          </template>
        </el-table-column>
        <el-table-column label="课时" width="90">
          <template #default="scope">
            <span class="mono">{{ scope.row.lesson_code || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="to_email_masked" label="收件人（脱敏）" min-width="170" />
        <el-table-column label="状态" width="100">
          <template #default="scope">
            <el-tag
              size="small"
              :type="STATUS_META[scope.row.status]?.type ?? 'info'"
            >
              {{ STATUS_META[scope.row.status]?.label ?? scope.row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="重试次数" width="90" align="center">
          <template #default="scope">{{ scope.row.retry_count ?? 0 }}</template>
        </el-table-column>
        <el-table-column label="发送时间（北京时间）" min-width="150">
          <template #default="scope">{{ formatBeijing(scope.row.sent_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="90" align="center">
          <template #default="scope">
            <el-button
              v-if="scope.row.status === 'failed'"
              size="small"
              type="warning"
              plain
              :loading="retryingId === scope.row.id"
              @click="retry(scope.row)"
            >
              重发
            </el-button>
            <span v-else class="text-muted">—</span>
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

.text-muted {
  color: #c0c4cc;
}

.pagination-bar {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
