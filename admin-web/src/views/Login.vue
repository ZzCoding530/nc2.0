<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { Lock, User } from '@element-plus/icons-vue'
import { post } from '../utils/request'
import { clearToken, setToken } from '../utils/auth'
import { useAuthStore } from '../stores/auth'

interface LoginResponse {
  token: string
  staff?: { name?: string }
  must_change_password?: boolean
}

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const mode = ref<'login' | 'change'>('login')

const loginFormRef = ref<FormInstance>()
const loginForm = reactive({ email: '', password: '' })
const loginRules: FormRules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' },
  ],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}
const loginLoading = ref(false)

const changeFormRef = ref<FormInstance>()
const changeForm = reactive({ old_password: '', new_password: '', confirm: '' })
const changeRules: FormRules = {
  old_password: [{ required: true, message: '请输入当前密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 8, message: '新密码至少 8 位', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (!/[A-Za-z]/.test(String(value)) || !/[0-9]/.test(String(value))) {
          callback(new Error('新密码需同时包含字母和数字'))
        } else {
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
  confirm: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (value !== changeForm.new_password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
}
const changeLoading = ref(false)
const changeEmail = ref('')

function redirectTarget(): string {
  const target = route.query.redirect
  return typeof target === 'string' && target.startsWith('/') && !target.startsWith('//')
    ? target
    : '/students'
}

async function handleLogin(): Promise<void> {
  try {
    await loginFormRef.value?.validate()
  } catch {
    return
  }
  loginLoading.value = true
  try {
    const res = await post<LoginResponse>('/admin/login', {
      email: loginForm.email,
      password: loginForm.password,
    })
    if (res.must_change_password) {
      // 首次登录：暂存 token（改密接口需要登录态），先完成改密
      if (res.token) setToken(res.token)
      changeEmail.value = loginForm.email
      changeForm.old_password = loginForm.password
      changeForm.new_password = ''
      changeForm.confirm = ''
      mode.value = 'change'
      ElMessage.info('首次登录，请先修改初始密码')
      return
    }
    auth.setSession(res.token, res.staff?.name ?? '运营')
    ElMessage.success('登录成功')
    router.replace(redirectTarget())
  } catch {
    // 错误信息已由统一拦截器提示
  } finally {
    loginLoading.value = false
  }
}

async function handleChangePassword(): Promise<void> {
  try {
    await changeFormRef.value?.validate()
  } catch {
    return
  }
  changeLoading.value = true
  try {
    await post('/admin/change-password', {
      old_password: changeForm.old_password,
      new_password: changeForm.new_password,
    })
    // 改密成功：清掉临时 token，用新密码重新登录
    clearToken()
    const res = await post<LoginResponse>('/admin/login', {
      email: changeEmail.value,
      password: changeForm.new_password,
    })
    auth.setSession(res.token, res.staff?.name ?? '运营')
    ElMessage.success('密码修改成功，已登录系统')
    router.replace(redirectTarget())
  } catch {
    // 停留在当前表单，错误已由统一拦截器提示
  } finally {
    changeLoading.value = false
  }
}

function backToLogin(): void {
  clearToken()
  mode.value = 'login'
}
</script>

<template>
  <div class="login-page">
    <el-card class="login-card" shadow="always">
      <div class="login-brand">
        <div class="login-title">NiceOffer 交付系统</div>
        <div class="login-subtitle">运营后台</div>
      </div>

      <template v-if="mode === 'login'">
        <el-form
          ref="loginFormRef"
          :model="loginForm"
          :rules="loginRules"
          size="large"
          @keyup.enter="handleLogin"
        >
          <el-form-item prop="email">
            <el-input v-model="loginForm.email" placeholder="邮箱" :prefix-icon="User" />
          </el-form-item>
          <el-form-item prop="password">
            <el-input
              v-model="loginForm.password"
              type="password"
              placeholder="密码"
              :prefix-icon="Lock"
              show-password
            />
          </el-form-item>
          <el-form-item>
            <el-button
              type="primary"
              class="login-button"
              :loading="loginLoading"
              @click="handleLogin"
            >
              登 录
            </el-button>
          </el-form-item>
        </el-form>
      </template>

      <template v-else>
        <el-alert
          class="change-alert"
          type="warning"
          :closable="false"
          show-icon
          title="首次登录需修改初始密码"
          :description="`账号：${changeEmail}`"
        />
        <el-form ref="changeFormRef" :model="changeForm" :rules="changeRules" label-width="92px">
          <el-form-item label="当前密码" prop="old_password">
            <el-input v-model="changeForm.old_password" type="password" show-password />
          </el-form-item>
          <el-form-item label="新密码" prop="new_password">
            <el-input
              v-model="changeForm.new_password"
              type="password"
              show-password
              placeholder="至少 8 位，含字母和数字"
            />
          </el-form-item>
          <el-form-item label="确认新密码" prop="confirm">
            <el-input v-model="changeForm.confirm" type="password" show-password />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="changeLoading" @click="handleChangePassword">
              修改密码并登录
            </el-button>
            <el-button @click="backToLogin">返回登录</el-button>
          </el-form-item>
        </el-form>
      </template>
    </el-card>
  </div>
</template>

<style scoped>
.login-page {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1f2d3d 0%, #2b3a4b 50%, #34495e 100%);
}

.login-card {
  width: 400px;
  border-radius: 8px;
}

.login-brand {
  text-align: center;
  margin-bottom: 24px;
}

.login-title {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.login-subtitle {
  margin-top: 6px;
  font-size: 13px;
  color: #909399;
  letter-spacing: 4px;
}

.login-button {
  width: 100%;
}

.change-alert {
  margin-bottom: 16px;
}
</style>
