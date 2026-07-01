<template>
  <div class="server-detail">
    <div class="page-header">
      <div style="display:flex;align-items:center;gap:4px">
        <el-button text @click="$router.push('/servers')">
          <el-icon><ArrowLeft /></el-icon>
        </el-button>
        <div>
          <h2>{{ server?.name }}</h2>
          <span class="server-info">{{ server?.host }}:{{ server?.port }} | {{ server?.username }}</span>
        </div>
      </div>
      <div class="header-actions">
        <el-button @click="handleRefreshAll" :loading="refreshingAll">
          <el-icon><Refresh /></el-icon> Refresh All
        </el-button>
        <el-button type="primary" @click="handleScan">
          <el-icon><Search /></el-icon> Scan Services
        </el-button>
        <el-button type="success" @click="addDialogVisible = true">
          <el-icon><Plus /></el-icon> Add Service
        </el-button>
      </div>
    </div>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="Services" name="services">
        <el-table :data="serviceStore.services" v-loading="serviceStore.loading" stripe>
          <el-table-column label="Service Name" min-width="140">
            <template #default="{ row }">
              {{ row.display_name || row.name }}
            </template>
          </el-table-column>
          <el-table-column label="Path" min-width="160" show-overflow-tooltip>
            <template #default="{ row }">
              <span v-if="row.custom_path" style="color:#409eff">{{ row.custom_path }}</span>
              <span v-else style="color:#909399">{{ server?.service_base_path }}/{{ row.name }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="Status" width="120">
            <template #default="{ row }">
              <el-tag :type="statusTagType(row.status)">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="Actions" width="540" fixed="right">
            <template #default="{ row }">
              <el-button size="small" @click="openEditService(row)">
                Edit
              </el-button>
              <el-button size="small" @click="handleRefreshStatus(row)">
                Refresh
              </el-button>
              <el-popconfirm title="Start this service?" @confirm="handleControl(row, 'start')">
                <template #reference>
                  <el-button size="small" type="success" :loading="controlLoading[row.id]?.start">
                    Start
                  </el-button>
                </template>
              </el-popconfirm>
              <el-popconfirm title="Stop this service?" @confirm="handleControl(row, 'stop')">
                <template #reference>
                  <el-button size="small" type="danger" :loading="controlLoading[row.id]?.stop">
                    Stop
                  </el-button>
                </template>
              </el-popconfirm>
              <el-popconfirm title="Restart this service?" @confirm="handleControl(row, 'restart')">
                <template #reference>
                  <el-button size="small" type="warning" :loading="controlLoading[row.id]?.restart">
                    Restart
                  </el-button>
                </template>
              </el-popconfirm>
              <el-button size="small" type="primary" @click="$router.push(`/services/${row.id}/config`)">
                Config
              </el-button>
              <el-button size="small" @click="$router.push(`/services/${row.id}/jars`)">
                JARs
              </el-button>
              <el-popconfirm title="Remove this service record?" @confirm="handleDelete(row.id)">
                <template #reference>
                  <el-button size="small">Del</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!serviceStore.loading && serviceStore.services.length === 0" description="No services. Click Scan Services to discover." />
      </el-tab-pane>

      <el-tab-pane label="Info" name="info">
        <el-descriptions :column="2" border v-if="server">
          <el-descriptions-item label="Name">{{ server.name }}</el-descriptions-item>
          <el-descriptions-item label="Host">{{ server.host }}</el-descriptions-item>
          <el-descriptions-item label="Port">{{ server.port }}</el-descriptions-item>
          <el-descriptions-item label="Username">{{ server.username }}</el-descriptions-item>
          <el-descriptions-item label="Auth Type">{{ server.auth_type }}</el-descriptions-item>
          <el-descriptions-item label="Service Base Path">{{ server.service_base_path }}</el-descriptions-item>
          <el-descriptions-item label="Created">{{ formatDateTime(server.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="Updated">{{ formatDateTime(server.updated_at) }}</el-descriptions-item>
        </el-descriptions>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="scanDialogVisible" title="Scan Results" width="500px">
      <div v-if="scanResult">
        <p><strong>Found on server:</strong> {{ scanResult.found.join(', ') || 'None' }}</p>
        <p><el-tag type="success">Added: {{ scanResult.added.length }}</el-tag></p>
        <p><el-tag type="info">Existing: {{ scanResult.existing.length }}</el-tag></p>
      </div>
      <template #footer>
        <el-button @click="scanDialogVisible = false">Close</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="editDialogVisible" title="Edit Service" width="500px" @closed="resetEditForm">
      <el-form :model="editForm" label-width="130px">
        <el-form-item label="Display Name">
          <el-input v-model="editForm.display_name" placeholder="Shown in UI, can differ from directory name" />
        </el-form-item>
        <el-form-item label="Directory Name">
          <el-input v-model="editForm.name" disabled />
          <span style="font-size:12px;color:#909399">Directory name on server (read-only)</span>
        </el-form-item>
        <el-form-item label="Custom Path">
          <el-input v-model="editForm.custom_path" placeholder="Leave empty for default" />
        </el-form-item>
        <el-form-item label="Control Method">
          <el-radio-group v-model="editForm.control_method">
            <el-radio value="auto">Auto (systemd then script)</el-radio>
            <el-radio value="systemd">systemd only</el-radio>
            <el-radio value="script">Script only (bin/script)</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">Cancel</el-button>
        <el-button type="primary" :loading="editLoading" @click="handleEditService">Save</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="addDialogVisible" title="Add Service" width="500px" @closed="resetAddForm">
      <el-form :model="addForm" label-width="110px">
        <el-form-item label="Service Name" required>
          <el-input v-model="addForm.name" placeholder="e.g. my-app" />
        </el-form-item>
        <el-form-item label="Custom Path">
          <el-input v-model="addForm.custom_path" placeholder="Leave empty for default path" />
          <span style="font-size:12px;color:#909399">
            Default: {{ server?.service_base_path }}/<strong>{{ addForm.name || '...' }}</strong>
          </span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addDialogVisible = false">Cancel</el-button>
        <el-button type="primary" :loading="addLoading" @click="handleAddService">Add</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useServerStore } from '@/stores/server'
import { useServiceStore } from '@/stores/service'
import { statusTagType, formatDateTime } from '@/utils/helpers'
import * as serverApi from '@/api/servers'
import * as serviceApi from '@/api/services'

const route = useRoute()
const serverStore = useServerStore()
const serviceStore = useServiceStore()

const server = ref(null)
const activeTab = ref('services')
const scanDialogVisible = ref(false)
const scanResult = ref(null)
const refreshingAll = ref(false)
const controlLoading = reactive({})
const addDialogVisible = ref(false)
const addLoading = ref(false)
const addForm = reactive({ name: '', custom_path: '' })

const editDialogVisible = ref(false)
const editLoading = ref(false)
const editForm = reactive({ name: '', display_name: '', custom_path: '', control_method: 'auto' })
const editingServiceId = ref(null)

async function loadServer() {
  const { data } = await serverApi.getServer(route.params.id)
  server.value = data
}

async function handleRefreshAll() {
  refreshingAll.value = true
  try {
    const { data } = await serviceApi.refreshAllStatus(route.params.id)
    await serviceStore.fetchServices(route.params.id)
    ElMessage.success(`Refreshed ${data.updated.length} services`)
  } catch (e) {
    ElMessage.error('Refresh failed')
  } finally {
    refreshingAll.value = false
  }
}

async function handleScan() {
  const result = await serviceStore.scanServices(route.params.id)
  scanResult.value = result
  scanDialogVisible.value = true
  await serviceStore.fetchServices(route.params.id)
}

async function handleRefreshStatus(row) {
  await serviceStore.refreshStatus(row.id)
  await serviceStore.fetchServices(route.params.id)
}

async function handleControl(row, action) {
  if (!controlLoading[row.id]) {
    controlLoading[row.id] = {}
  }
  controlLoading[row.id][action] = true
  try {
    let result
    if (action === 'start') result = await serviceApi.startService(row.id)
    else if (action === 'stop') result = await serviceApi.stopService(row.id)
    else if (action === 'restart') result = await serviceApi.restartService(row.id)

    if (result.data.success) {
      ElMessage.success(`${action} ${row.name}: ${result.data.message || 'OK'}`)
    } else {
      ElMessage.warning(`${action} ${row.name}: ${result.data.message || 'Failed'}`)
    }
    await handleRefreshStatus(row)
  } catch (e) {
    ElMessage.error(`${action} failed: ${e.response?.data?.detail || e.message}`)
  } finally {
    controlLoading[row.id][action] = false
  }
}

async function handleDelete(id) {
  await serviceStore.deleteService(id)
  await serviceStore.fetchServices(route.params.id)
  ElMessage.success('Service record removed')
}

function resetAddForm() {
  addForm.name = ''
  addForm.custom_path = ''
}

function openEditService(row) {
  editingServiceId.value = row.id
  editForm.name = row.name
  editForm.display_name = row.display_name || ''
  editForm.custom_path = row.custom_path || ''
  editForm.control_method = row.control_method || 'auto'
  editDialogVisible.value = true
}

function resetEditForm() {
  editingServiceId.value = null
}

async function handleEditService() {
  editLoading.value = true
  try {
    await serviceApi.updateService(editingServiceId.value, {
      display_name: editForm.display_name || null,
      custom_path: editForm.custom_path || null,
      control_method: editForm.control_method,
    })
    ElMessage.success('Service updated')
    editDialogVisible.value = false
    await serviceStore.fetchServices(route.params.id)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || 'Update failed')
  } finally {
    editLoading.value = false
  }
}

async function handleAddService() {
  if (!addForm.name.trim()) {
    ElMessage.warning('Service name is required')
    return
  }
  addLoading.value = true
  try {
    await serviceApi.createService(route.params.id, {
      name: addForm.name.trim(),
      custom_path: addForm.custom_path.trim() || null,
    })
    ElMessage.success('Service added')
    addDialogVisible.value = false
    await serviceStore.fetchServices(route.params.id)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || 'Failed to add service')
  } finally {
    addLoading.value = false
  }
}

onMounted(async () => {
  await loadServer()
  serviceStore.fetchServices(route.params.id)
})
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.page-header h2 {
  margin: 0 0 4px 0;
}
.server-info {
  font-size: 13px;
  color: #909399;
}
.header-actions {
  display: flex;
  gap: 8px;
}
</style>
