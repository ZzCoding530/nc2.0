<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { Calendar, Message, SwitchButton, User, View } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const menus = [
  { path: '/students', title: '学员管理', icon: User },
  { path: '/schedules', title: '排期管理', icon: Calendar },
  { path: '/emails', title: '邮件中心', icon: Message },
  { path: '/preview', title: '学员视图预览', icon: View },
]

async function handleLogout(): Promise<void> {
  try {
    await ElMessageBox.confirm('确定退出登录？', '提示', {
      type: 'warning',
      confirmButtonText: '退出',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <el-container class="layout">
    <el-aside width="224px" class="aside">
      <div class="brand">
        <div class="brand-name">NiceOffer 交付系统</div>
        <div class="brand-sub">运营后台</div>
      </div>
      <el-menu :default-active="route.path" router class="menu">
        <el-menu-item v-for="m in menus" :key="m.path" :index="m.path">
          <el-icon><component :is="m.icon" /></el-icon>
          <span>{{ m.title }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container class="right">
      <el-header class="header">
        <div class="header-title">{{ route.meta.title ?? '' }}</div>
        <div class="header-right">
          <el-icon class="staff-icon"><User /></el-icon>
          <span class="staff-name">{{ auth.staffName || '运营' }}</span>
          <el-divider direction="vertical" />
          <el-button :icon="SwitchButton" link class="logout-btn" @click="handleLogout">
            退出登录
          </el-button>
        </div>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.layout {
  height: 100%;
}

.aside {
  background-color: #fff;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
}

.brand {
  padding: 20px 20px 16px;
  border-bottom: 1px solid #f0f2f5;
}

.brand-name {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.brand-sub {
  margin-top: 4px;
  font-size: 12px;
  color: #909399;
  letter-spacing: 2px;
}

.menu {
  border-right: none;
  padding-top: 8px;
}

.right {
  min-width: 0;
}

.header {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background-color: #fff;
  border-bottom: 1px solid #e4e7ed;
}

.header-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.staff-icon {
  color: #909399;
}

.staff-name {
  color: #606266;
}

.logout-btn {
  color: #909399;
}

.logout-btn:hover {
  color: #f56c6c;
}

.main {
  padding: 16px;
  overflow-y: auto;
}
</style>
