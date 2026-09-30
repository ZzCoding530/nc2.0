<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { FullScreen } from '@element-plus/icons-vue'
import { get } from '../utils/request'

interface StudentOption {
  id: number
  name: string
  cohort?: string
}

const students = ref<StudentOption[]>([])
const studentId = ref<number | null>(null)
const baseUrl = ref('http://localhost:5173')
const loading = ref(false)

const previewUrl = computed<string>(() => {
  if (!studentId.value) return ''
  const base = baseUrl.value.trim().replace(/\/+$/, '')
  if (!base) return ''
  return `${base}/?student_id=${studentId.value}`
})

async function loadStudents(): Promise<void> {
  loading.value = true
  try {
    const res = await get<{ items?: StudentOption[] }>('/admin/students', {
      page: 1,
      page_size: 100,
    })
    students.value = res.items ?? []
  } catch {
    // 错误已由统一拦截器提示
  } finally {
    loading.value = false
  }
}

function openInNewWindow(): void {
  if (!previewUrl.value) {
    ElMessage.warning('请先选择学员')
    return
  }
  window.open(previewUrl.value, '_blank')
}

onMounted(loadStudents)
</script>

<template>
  <div class="page">
    <el-card shadow="never" class="filter-card">
      <div class="filter-bar">
        <div class="filter-item">
          <span class="filter-label">学员</span>
          <el-select
            v-model="studentId"
            filterable
            clearable
            :loading="loading"
            placeholder="选择要预览的学员"
            style="width: 240px"
          >
            <el-option
              v-for="s in students"
              :key="s.id"
              :label="s.name + (s.cohort ? `（${s.cohort}）` : '')"
              :value="s.id"
            />
          </el-select>
        </div>
        <div class="filter-item">
          <span class="filter-label">学员端地址</span>
          <el-input
            v-model="baseUrl"
            placeholder="http://localhost:5173"
            style="width: 280px"
          />
        </div>
        <el-button
          type="primary"
          :icon="FullScreen"
          :disabled="!previewUrl"
          @click="openInNewWindow"
        >
          在新窗口打开
        </el-button>
      </div>
      <div class="preview-tip">
        预览通过 URL 参数 <code>?student_id=X</code>
        以该学员视角打开学员端 H5（课表 / 首页），用于上架前核对内容；默认指向学员端本地开发服务器。
      </div>
    </el-card>

    <el-card shadow="never">
      <div v-if="previewUrl" class="phone-wrap">
        <div class="phone-frame">
          <iframe :src="previewUrl" title="学员视图预览" class="phone-iframe" />
        </div>
        <div class="phone-url mono">{{ previewUrl }}</div>
      </div>
      <el-empty v-else description="请先选择学员" />
    </el-card>
  </div>
</template>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.filter-card :deep(.el-card__body) {
  padding-bottom: 12px;
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

.preview-tip {
  margin-top: 12px;
  font-size: 12px;
  color: #909399;
  line-height: 1.6;
}

.preview-tip code {
  background: #f4f4f5;
  padding: 1px 6px;
  border-radius: 3px;
  color: #476582;
}

.phone-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
}

.phone-frame {
  width: 391px;
  height: 716px;
  border: 8px solid #2c2c2e;
  border-radius: 28px;
  overflow: hidden;
  background: #fff;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

.phone-iframe {
  width: 100%;
  height: 100%;
  border: none;
  display: block;
}

.phone-url {
  font-size: 12px;
  color: #909399;
}
</style>
