<template>
  <el-container style="min-height: 100vh">
    <el-aside :width="isCollapsed ? '64px' : '220px'" class="sidebar-container">
      <div class="sidebar-logo">
        <h2 v-if="!isCollapsed">JSM</h2>
        <span v-if="!isCollapsed">Java Service Manager</span>
        <h2 v-else class="sidebar-logo-collapsed">J</h2>
      </div>
      <el-menu
        :default-active="activeMenu"
        router
        :collapse="isCollapsed"
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409eff"
        class="sidebar-menu"
      >
        <el-menu-item index="/servers">
          <el-icon><Monitor /></el-icon>
          <template #title>Servers</template>
        </el-menu-item>
        <el-menu-item index="/multi-server">
          <el-icon><Operation /></el-icon>
          <template #title>Batch Operations</template>
        </el-menu-item>
        <el-menu-item index="/operations">
          <el-icon><Tickets /></el-icon>
          <template #title>Operation Logs</template>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header>
        <div class="header-left">
          <el-icon class="collapse-btn" @click="isCollapsed = !isCollapsed">
            <Fold v-if="!isCollapsed" />
            <Expand v-else />
          </el-icon>
          <div class="header-breadcrumb">
            <el-breadcrumb>
              <el-breadcrumb-item :to="{ path: '/' }">Home</el-breadcrumb-item>
              <el-breadcrumb-item
                v-for="(crumb, idx) in breadcrumbs"
                :key="crumb.path"
                :to="idx < breadcrumbs.length - 1 ? { path: crumb.path } : undefined"
              >
                {{ crumb.label }}
              </el-breadcrumb-item>
            </el-breadcrumb>
          </div>
        </div>
        <div class="header-right">
          <el-dropdown trigger="click" @command="handleUserCommand">
            <span class="user-info">
              <el-icon><UserFilled /></el-icon>
              <span class="username">{{ authStore.username || 'admin' }}</span>
              <el-icon class="arrow-icon"><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="changePassword">
                  <el-icon><Edit /></el-icon>
                  修改密码
                </el-dropdown-item>
                <el-dropdown-item command="logout" divided>
                  <el-icon><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>

    <!-- Change Password Dialog -->
    <el-dialog v-model="passwordDialogVisible" title="修改密码" width="420px" :close-on-click-modal="false">
      <el-form
        ref="passwordFormRef"
        :model="passwordForm"
        :rules="passwordRules"
        label-width="100px"
        @submit.prevent="handleChangePassword"
      >
        <el-form-item label="原密码" prop="oldPassword">
          <el-input
            v-model="passwordForm.oldPassword"
            type="password"
            placeholder="请输入原密码"
            show-password
          />
        </el-form-item>
        <el-form-item label="新密码" prop="newPassword">
          <el-input
            v-model="passwordForm.newPassword"
            type="password"
            placeholder="请输入新密码"
            show-password
          />
        </el-form-item>
        <el-form-item label="确认新密码" prop="confirmPassword">
          <el-input
            v-model="passwordForm.confirmPassword"
            type="password"
            placeholder="请再次输入新密码"
            show-password
            @keyup.enter="handleChangePassword"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="passwordDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="passwordLoading" @click="handleChangePassword">
          确认修改
        </el-button>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup>
import { computed, ref, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const isCollapsed = ref(false)

// --- Password dialog ---
const passwordDialogVisible = ref(false)
const passwordLoading = ref(false)
const passwordFormRef = ref(null)

const passwordForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
})

const validateConfirmPassword = (_rule, value) => {
  if (value !== passwordForm.newPassword) {
    return Promise.reject(new Error('两次输入的密码不一致'))
  }
  return Promise.resolve()
}

const passwordRules = {
  oldPassword: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  newPassword: [{ required: true, message: '请输入新密码', trigger: 'blur' }],
  confirmPassword: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' },
  ],
}

function handleChangePassword() {
  passwordFormRef.value?.validate((valid) => {
    if (!valid) return
    passwordLoading.value = true
    const result = authStore.changePassword(passwordForm.oldPassword, passwordForm.newPassword)
    if (result.success) {
      ElMessage.success('密码修改成功')
      passwordDialogVisible.value = false
      passwordForm.oldPassword = ''
      passwordForm.newPassword = ''
      passwordForm.confirmPassword = ''
    } else {
      ElMessage.error(result.message)
    }
    passwordLoading.value = false
  })
}

// --- User dropdown ---
function handleUserCommand(command) {
  if (command === 'changePassword') {
    passwordForm.oldPassword = ''
    passwordForm.newPassword = ''
    passwordForm.confirmPassword = ''
    passwordDialogVisible.value = true
  } else if (command === 'logout') {
    authStore.logout()
    router.push('/login')
  }
}

const activeMenu = computed(() => {
  const path = route.path
  if (path.startsWith('/servers')) return '/servers'
  if (path.startsWith('/services')) return ''
  return path
})
const breadcrumbs = computed(() => {
  const path = route.path
  const segments = path.split('/').filter(Boolean)
  const crumbs = []
  let acc = ''

  const labelMap = {
    servers: 'Servers',
    services: 'Services',
    config: 'Config',
    jars: 'JARs',
    'multi-server': 'Batch Operations',
    operations: 'Operation Logs',
  }

  for (const seg of segments) {
    acc += '/' + seg
    if (/^\d+$/.test(seg)) continue
    if (labelMap[seg]) {
      crumbs.push({ label: labelMap[seg], path: acc })
    }
  }
  return crumbs
})
</script>

<style scoped>
.sidebar-container {
  background-color: #304156;
  transition: width 0.3s ease;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.sidebar-logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #263445;
  color: #fff;
  gap: 8px;
  flex-shrink: 0;
  transition: all 0.3s ease;
}
.sidebar-logo h2 {
  margin: 0;
  font-size: 18px;
  white-space: nowrap;
}
.sidebar-logo span {
  font-size: 12px;
  color: #bfcbd9;
  white-space: nowrap;
}
.sidebar-logo-collapsed {
  font-size: 20px !important;
}
.sidebar-menu {
  border-right: none;
  flex: 1;
  overflow-y: auto;
}
.el-header {
  background: #fff;
  border-bottom: 1px solid #e6e6e6;
  display: flex;
  align-items: center;
  padding: 0 20px;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.collapse-btn {
  font-size: 20px;
  cursor: pointer;
  color: #606266;
  transition: color 0.2s;
  flex-shrink: 0;
}
.collapse-btn:hover {
  color: #409eff;
}
.header-breadcrumb {
  display: flex;
  align-items: center;
}
.header-right {
  margin-left: auto;
  display: flex;
  align-items: center;
}
.user-info {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  color: #606266;
  font-size: 14px;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background-color 0.2s;
}
.user-info:hover {
  background-color: #f5f7fa;
}
.username {
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.arrow-icon {
  font-size: 12px;
  color: #909399;
}
</style>
