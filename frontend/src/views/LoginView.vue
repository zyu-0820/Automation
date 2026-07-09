<template>
  <div class="login-container">
    <div class="login-card">
      <h2 class="login-title">Java Service Manager</h2>
      <p class="login-subtitle">请登录以继续</p>
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @submit.prevent="handleLogin"
      >
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="form.username"
            placeholder="请输入用户名"
            size="large"
          >
            <template #prefix>
              <el-icon><User /></el-icon>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            size="large"
            show-password
            @keyup.enter="handleLogin"
          >
            <template #prefix>
              <el-icon><Lock /></el-icon>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            style="width: 100%"
            @click="handleLogin"
          >
            登 录
          </el-button>
        </el-form-item>
      </el-form>
      <p v-if="errorMsg" class="login-error">{{ errorMsg }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const formRef = ref(null)
const loading = ref(false)
const errorMsg = ref('')

const form = reactive({
  username: '',
  password: '',
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

function handleLogin() {
  formRef.value?.validate((valid) => {
    if (!valid) return

    loading.value = true
    errorMsg.value = ''

    // Simulate a small delay for UX
    setTimeout(() => {
      const result = authStore.login(form.username, form.password)
      if (result.success) {
        const redirect = route.query.redirect || '/'
        router.push(redirect)
      } else {
        errorMsg.value = result.message
      }
      loading.value = false
    }, 300)
  })
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #304156 0%, #1f2d3d 50%, #263445 100%);
}
.login-card {
  width: 400px;
  padding: 40px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}
.login-title {
  margin: 0 0 4px;
  text-align: center;
  font-size: 22px;
  color: #303133;
}
.login-subtitle {
  margin: 0 0 28px;
  text-align: center;
  font-size: 14px;
  color: #909399;
}
.login-error {
  margin: 0;
  text-align: center;
  color: #f56c6c;
  font-size: 13px;
}
</style>
