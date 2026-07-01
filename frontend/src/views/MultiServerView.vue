<template>
  <div class="multi-view">
    <h2>Batch Operations</h2>
    <p class="desc">Push the same config file or JAR to multiple services across servers.</p>

    <el-steps :active="step" align-center style="margin: 24px 0">
      <el-step title="Select Services" />
      <el-step title="Choose Operation" />
      <el-step title="Execute" />
    </el-steps>

    <!-- Step 1: Select services -->
    <div v-if="step === 0">
      <div v-for="srv in serverStore.servers" :key="srv.id" style="margin-bottom: 16px">
        <el-card shadow="hover">
          <template #header>
            <el-checkbox
              v-model="serverChecks[srv.id]"
              @change="(val) => { if(val) loadServicesForServer(srv.id) }"
            >
              <strong>{{ srv.name }}</strong> <span class="host-info">{{ srv.host }}:{{ srv.port }}</span>
            </el-checkbox>
          </template>
          <div v-if="serverChecks[srv.id] && servicesByServer[srv.id]">
            <el-checkbox-group v-model="selectedServiceIds">
              <el-tag
                v-for="svc in servicesByServer[srv.id]"
                :key="svc.id"
                :type="selectedServiceIds.includes(svc.id) ? 'primary' : 'info'"
                class="service-tag"
                @click="toggleService(svc.id)"
              >
                {{ svc.name }}
              </el-tag>
            </el-checkbox-group>
            <el-empty v-if="servicesByServer[srv.id]?.length === 0" description="No services" />
          </div>
        </el-card>
      </div>
      <div style="margin-top: 16px">
        <span style="margin-right: 12px; color: #606266">
          Selected: <strong>{{ selectedServiceIds.length }}</strong> services
        </span>
        <el-button type="primary" :disabled="selectedServiceIds.length === 0" @click="step = 1">
          Next
        </el-button>
      </div>
    </div>

    <!-- Step 2: Choose operation & content -->
    <div v-if="step === 1">
      <el-radio-group v-model="operationType" size="large">
        <el-radio-button value="config">Update Config File</el-radio-button>
        <el-radio-button value="jar">Upload JAR File</el-radio-button>
      </el-radio-group>

      <div v-if="operationType === 'config'" style="margin-top: 16px">
        <div class="config-step2">
          <div class="config-meta">
            <div>
              <label>Config File</label>
              <el-select
                v-model="configFilename"
                filterable
                allow-create
                default-first-option
                placeholder="Pick existing or type new filename"
                style="width: 100%"
              >
                <el-option
                  v-for="f in commonConfigFiles"
                  :key="f.name"
                  :label="f.name + ' (' + f.dir + ')'"
                  :value="f.name"
                />
              </el-select>
            </div>
            <div>
              <label>Target Directory</label>
              <el-select v-model="configDir" style="width: 100%">
                <el-option v-for="d in configDirs" :key="d" :label="d" :value="d" />
              </el-select>
            </div>
            <div>
              <label>Load content from</label>
              <el-select
                v-model="loadFromServiceId"
                placeholder="Optional"
                clearable
                value-key="id"
                @change="handleLoadContent"
                style="width: 100%"
              >
                <el-option
                  v-for="svc in flatSelectedServices"
                  :key="svc.id"
                  :label="(svc.serverName || 'Server ' + svc.server_id) + ' / ' + svc.name"
                  :value="svc.id"
                />
              </el-select>
            </div>
          </div>
          <div style="display:flex;align-items:center;gap:12px;margin:12px 0 4px">
            <label>Content</label>
            <el-radio-group v-model="configMode" size="small">
              <el-radio value="overwrite">Overwrite</el-radio>
              <el-radio value="append">Append</el-radio>
            </el-radio-group>
          </div>
          <el-input
            v-model="configContent"
            type="textarea"
            :rows="18"
            :placeholder="configMode === 'append' ? 'Content to append to the end of the file...' : 'Enter config content, or select a service above to load existing content...'"
            style="font-family: monospace; font-size: 13px"
          />
        </div>
      </div>

      <div v-if="operationType === 'jar'" style="margin-top: 16px">
        <el-upload
          drag
          :auto-upload="false"
          :limit="1"
          accept=".jar"
          :on-change="(f) => batchJarFile = f.raw"
        >
          <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
          <div class="el-upload__text">Drop JAR file here</div>
        </el-upload>
      </div>

      <div style="margin-top: 16px">
        <el-button @click="step = 0">Back</el-button>
        <el-button type="primary" @click="step = 2">Next</el-button>
      </div>
    </div>

    <!-- Step 3: Confirm & execute -->
    <div v-if="step === 2">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="Operation">{{ operationType === 'config' ? (configMode === 'append' ? 'Append Config' : 'Update Config') : 'Upload JAR' }}</el-descriptions-item>
        <el-descriptions-item label="Target Services">{{ selectedServiceIds.length }}</el-descriptions-item>
        <el-descriptions-item v-if="operationType === 'config'" label="File">{{ configDir }}/{{ configFilename }}</el-descriptions-item>
        <el-descriptions-item v-if="operationType === 'config'" label="Mode">{{ configMode === 'append' ? 'Append' : 'Overwrite' }}</el-descriptions-item>
        <el-descriptions-item v-if="operationType === 'jar'" label="File">{{ batchJarFile?.name }}</el-descriptions-item>
      </el-descriptions>

      <div style="margin-top: 16px">
        <el-button @click="step = 1">Back</el-button>
        <el-button type="primary" :loading="executing" @click="handleExecute">
          Execute
        </el-button>
      </div>

      <div v-if="batchResult" style="margin-top: 16px">
        <el-alert
          :type="batchResult.summary.failure === 0 ? 'success' : 'warning'"
          :closable="false"
          show-icon
        >
          Total: {{ batchResult.summary.total }} | Success: {{ batchResult.summary.success }} | Failed: {{ batchResult.summary.failure }}
        </el-alert>
        <el-table :data="batchResult.results" stripe style="margin-top: 8px">
          <el-table-column prop="server_name" label="Server" min-width="120" />
          <el-table-column prop="service_name" label="Service" min-width="120" />
          <el-table-column prop="status" label="Status" width="100">
            <template #default="{ row }">
              <el-tag :type="row.status === 'success' ? 'success' : 'danger'">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="message" label="Message" />
        </el-table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useServerStore } from '@/stores/server'
import * as serviceApi from '@/api/services'
import * as configApi from '@/api/configs'
import * as operationApi from '@/api/operations'

const serverStore = useServerStore()

const step = ref(0)
const serverChecks = reactive({})
const servicesByServer = reactive({})
const selectedServiceIds = ref([])
const operationType = ref('config')
const configFilename = ref('')
const configDir = ref('conf')
const configDirs = ref(['conf', 'config'])
const configMode = ref('overwrite')
const loadFromServiceId = ref(null)
const configContent = ref('')
const commonConfigFiles = ref([])
const batchJarFile = ref(null)
const executing = ref(false)
const batchResult = ref(null)

const flatSelectedServices = computed(() => {
  const result = []
  for (const serverId in serverChecks) {
    if (!serverChecks[serverId]) continue
    const server = serverStore.servers.find(s => s.id === parseInt(serverId))
    const svcs = servicesByServer[serverId] || []
    for (const svc of svcs) {
      if (selectedServiceIds.value.includes(svc.id)) {
        result.push({ ...svc, serverName: server?.name || serverId })
      }
    }
  }
  return result
})

function toggleService(id) {
  const idx = selectedServiceIds.value.indexOf(id)
  if (idx >= 0) {
    selectedServiceIds.value.splice(idx, 1)
  } else {
    selectedServiceIds.value.push(id)
  }
}

async function loadServicesForServer(serverId) {
  const { data } = await serviceApi.getServices(serverId)
  servicesByServer[serverId] = data
}

async function loadConfigFilesForSelected() {
  if (selectedServiceIds.value.length === 0) return
  commonConfigFiles.value = []
  try {
    // fetch config files from all selected services, find common ones
    const allFiles = new Map()
    for (const svcId of selectedServiceIds.value.slice(0, 5)) {
      try {
        const { data } = await configApi.getConfigFiles(svcId)
        for (const f of data) {
          const key = f.name
          if (!allFiles.has(key)) {
            allFiles.set(key, { names: new Set(), dirs: new Set() })
          }
          allFiles.get(key).names.add(key)
          allFiles.get(key).dirs.add(f.dir)
        }
      } catch {}
    }

    const dirs = new Set(['conf', 'config'])
    const files = []
    for (const [name, info] of allFiles) {
      files.push({ name, dir: [...info.dirs][0] })
      info.dirs.forEach(d => dirs.add(d))
    }
    commonConfigFiles.value = files
    configDirs.value = [...dirs]
  } catch {}
}

watch(step, async (val) => {
  if (val === 1 && operationType.value === 'config') {
    await loadConfigFilesForSelected()
  }
})

watch(operationType, async (val) => {
  if (val === 'config' && step.value === 1) {
    await loadConfigFilesForSelected()
  }
})

async function handleLoadContent(svcId) {
  if (!svcId || !configFilename.value) return
  try {
    const { data } = await configApi.getConfigContent(svcId, configFilename.value, configDir.value)
    configContent.value = data.content
    ElMessage.success('Content loaded')
  } catch (e) {
    ElMessage.warning('Could not load content from this service')
  }
}

async function handleExecute() {
  executing.value = true
  batchResult.value = null
  try {
    let result
    if (operationType.value === 'config') {
      result = await operationApi.batchUpdateConfig(
        selectedServiceIds.value,
        configFilename.value,
        configContent.value,
        configDir.value,
        configMode.value
      )
    } else {
      result = await operationApi.batchUploadJar(
        selectedServiceIds.value,
        batchJarFile.value
      )
    }
    batchResult.value = result.data
    ElMessage.success('Batch operation completed')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || 'Batch operation failed')
  } finally {
    executing.value = false
  }
}

onMounted(() => {
  serverStore.fetchServers()
})
</script>

<style scoped>
.desc {
  color: #909399;
  font-size: 14px;
  margin: 0;
}
.host-info {
  font-weight: normal;
  color: #909399;
  font-size: 12px;
  margin-left: 8px;
}
.service-tag {
  cursor: pointer;
  margin: 4px;
  user-select: none;
}
.config-step2 {
  display: flex;
  flex-direction: column;
}
.config-meta {
  display: flex;
  gap: 16px;
}
.config-meta > div {
  flex: 1;
}
.config-meta label {
  display: block;
  font-size: 13px;
  color: #606266;
  margin-bottom: 4px;
}
</style>
