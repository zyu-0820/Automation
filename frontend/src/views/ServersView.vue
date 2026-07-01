<template>
  <div class="servers-view">
    <div class="page-header">
      <h2>Servers</h2>
      <el-button type="primary" @click="showDialog = true">
        <el-icon><Plus /></el-icon> Add Server
      </el-button>
    </div>

    <el-table :data="store.servers" v-loading="store.loading" stripe>
      <el-table-column prop="name" label="Name" min-width="120" />
      <el-table-column prop="host" label="Host" min-width="140" />
      <el-table-column prop="port" label="Port" width="80" />
      <el-table-column prop="username" label="User" width="100" />
      <el-table-column prop="service_base_path" label="Service Path" min-width="180" />
      <el-table-column label="Actions" width="320" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="handleTestConnection(row)">
            Test {{ testingId === row.id ? '...' : '' }}
          </el-button>
          <el-button size="small" type="primary" @click="$router.push(`/servers/${row.id}`)">
            Detail
          </el-button>
          <el-button size="small" @click="openEdit(row)">Edit</el-button>
          <el-popconfirm title="Delete this server?" @confirm="handleDelete(row.id)">
            <template #reference>
              <el-button size="small" type="danger">Delete</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog
      v-model="showDialog"
      :title="editingServer ? 'Edit Server' : 'Add Server'"
      width="600px"
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="140px">
        <el-form-item label="Name" prop="name">
          <el-input v-model="form.name" placeholder="e.g. prod-server-1" />
        </el-form-item>
        <el-form-item label="Host" prop="host">
          <el-input v-model="form.host" placeholder="192.168.1.100" />
        </el-form-item>
        <el-form-item label="Port" prop="port">
          <el-input-number v-model="form.port" :min="1" :max="65535" />
        </el-form-item>
        <el-form-item label="Username" prop="username">
          <el-input v-model="form.username" placeholder="root" />
        </el-form-item>
        <el-form-item label="Auth Type" prop="auth_type">
          <el-radio-group v-model="form.auth_type">
            <el-radio value="password">Password</el-radio>
            <el-radio value="key">Private Key</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="form.auth_type === 'password'" label="Password" prop="password">
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
        <el-form-item v-if="form.auth_type === 'key'" label="Private Key" prop="private_key">
          <el-input v-model="form.private_key" type="textarea" :rows="4" />
        </el-form-item>
        <el-divider content-position="left">Privilege Escalation</el-divider>
        <el-form-item label="Become Method">
          <el-select v-model="form.become_method" clearable placeholder="None (no escalation)">
            <el-option label="sudo" value="sudo" />
            <el-option label="su" value="su" />
          </el-select>
        </el-form-item>
        <el-form-item label="Become User">
          <el-input v-model="form.become_user" placeholder="root" />
        </el-form-item>
        <el-form-item v-if="form.become_method" label="Become Password">
          <el-input v-model="form.become_password" type="password" show-password />
        </el-form-item>
        <el-form-item label="Config Extensions" prop="config_extensions">
          <el-input v-model="form.config_extensions" placeholder="yml,yaml,xml" />
          <span style="font-size:12px;color:#909399">Comma-separated file extensions to scan in conf/config dirs</span>
        </el-form-item>
        <el-form-item label="Service Base Path" prop="service_base_path">
          <el-input v-model="form.service_base_path" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">Cancel</el-button>
        <el-button type="primary" @click="handleSubmit">Save</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useServerStore } from '@/stores/server'

const store = useServerStore()
const showDialog = ref(false)
const editingServer = ref(null)
const testingId = ref(null)
const formRef = ref(null)

const defaultForm = {
  name: '',
  host: '',
  port: 22,
  username: 'root',
  auth_type: 'password',
  password: '',
  private_key: '',
  become_method: '',
  become_user: '',
  become_password: '',
  config_extensions: 'yml,yaml,xml',
  service_base_path: '/home/apps/services',
}

const form = reactive({ ...defaultForm })

const rules = {
  name: [{ required: true, message: 'Required', trigger: 'blur' }],
  host: [{ required: true, message: 'Required', trigger: 'blur' }],
  username: [{ required: true, message: 'Required', trigger: 'blur' }],
}

function resetForm() {
  editingServer.value = null
  Object.assign(form, { ...defaultForm })
}

function openEdit(row) {
  editingServer.value = row
  Object.assign(form, {
    name: row.name,
    host: row.host,
    port: row.port,
    username: row.username,
    auth_type: row.auth_type,
    password: '',
    private_key: '',
    become_method: row.become_method || '',
    become_user: row.become_user || '',
    become_password: '',
    config_extensions: row.config_extensions || 'yml,yaml,xml',
    service_base_path: row.service_base_path,
  })
  showDialog.value = true
}

async function handleSubmit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  if (editingServer.value) {
    const data = { ...form }
    if (!data.password) delete data.password
    if (!data.private_key) delete data.private_key
    if (!data.become_password) delete data.become_password
    if (!data.become_user) delete data.become_user
    await store.updateServer(editingServer.value.id, data)
    ElMessage.success('Server updated')
  } else {
    await store.createServer(form)
    ElMessage.success('Server added')
  }
  showDialog.value = false
}

async function handleTestConnection(row) {
  testingId.value = row.id
  try {
    const result = await store.testConnection(row.id)
    if (result.success) {
      ElMessage.success(`Connected to ${row.name}: ${result.message}`)
    } else {
      ElMessage.error(`Failed: ${result.message}`)
    }
  } finally {
    testingId.value = null
  }
}

async function handleDelete(id) {
  await store.deleteServer(id)
  ElMessage.success('Server deleted')
}

onMounted(() => {
  store.fetchServers()
})
</script>

<style scoped>
.servers-view {
  padding: 0;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.page-header h2 {
  margin: 0;
}
</style>
