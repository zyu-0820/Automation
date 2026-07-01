<template>
  <div class="jars-view">
    <div class="page-header">
      <div style="display:flex;align-items:center;gap:4px">
        <el-button text @click="$router.back()">
          <el-icon><ArrowLeft /></el-icon>
        </el-button>
        <div>
          <h2>JAR Management</h2>
          <span class="subtitle" v-if="service">{{ service.name }}</span>
        </div>
      </div>
      <el-button type="primary" @click="uploadDialogVisible = true">
        <el-icon><Upload /></el-icon> Upload JAR
      </el-button>
    </div>

    <el-table :data="jars" stripe v-loading="loading">
      <el-table-column prop="name" label="Filename" min-width="200" />
      <el-table-column label="Size" width="120">
        <template #default="{ row }">{{ formatFileSize(row.size) }}</template>
      </el-table-column>
      <el-table-column label="Modified" width="180">
        <template #default="{ row }">{{ row.modified_at }}</template>
      </el-table-column>
      <el-table-column label="Actions" width="120" fixed="right">
        <template #default="{ row }">
          <el-popconfirm
            title="Delete this JAR?"
            @confirm="handleDelete(row.name)"
          >
            <template #reference>
              <el-button size="small" type="danger">Delete</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!loading && jars.length === 0" description="No JAR files found" />

    <el-dialog v-model="uploadDialogVisible" title="Upload JAR" width="500px" @closed="uploadFile = null">
      <div class="upload-section">
        <el-upload
          ref="uploadRef"
          drag
          :auto-upload="false"
          :limit="1"
          accept=".jar"
          :on-change="handleFileChange"
          :on-remove="() => uploadFile = null"
        >
          <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
          <div class="el-upload__text">Drop JAR file here or click to browse</div>
          <template #tip>
            <div class="el-upload__tip">Only .jar files are accepted</div>
          </template>
        </el-upload>

        <el-alert
          v-if="existingJar"
          type="warning"
          :closable="false"
          show-icon
          style="margin-top: 12px"
        >
          Existing JAR <strong>{{ existingJar.name }}</strong> ({{ formatFileSize(existingJar.size) }}) will be backed up and replaced.
        </el-alert>

        <div class="upload-actions" style="margin-top: 16px; text-align: right">
          <el-button @click="uploadDialogVisible = false">Cancel</el-button>
          <el-button
            type="primary"
            :loading="uploading"
            :disabled="!uploadFile"
            @click="handleUpload"
          >
            Upload & Replace
          </el-button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import * as jarApi from '@/api/jars'
import * as serviceApi from '@/api/services'
import { formatFileSize } from '@/utils/helpers'

const route = useRoute()
const serviceId = ref(parseInt(route.params.id))
const service = ref(null)
const jars = ref([])
const loading = ref(false)
const uploadDialogVisible = ref(false)
const uploadFile = ref(null)
const uploading = ref(false)

const existingJar = computed(() => {
  if (!uploadFile.value) return null
  return jars.value.find(j => j.name === uploadFile.value.name) || null
})

async function loadService() {
  const { data } = await serviceApi.getService(serviceId.value)
  service.value = data
}

async function loadJars() {
  loading.value = true
  try {
    const { data } = await jarApi.getJars(serviceId.value)
    jars.value = data
  } finally {
    loading.value = false
  }
}

function handleFileChange(file) {
  uploadFile.value = file.raw
}

async function handleUpload() {
  if (!uploadFile.value) return
  uploading.value = true
  try {
    await jarApi.uploadJar(serviceId.value, uploadFile.value)
    ElMessage.success('JAR uploaded. Original file backed up.')
    uploadDialogVisible.value = false
    uploadFile.value = null
    await loadJars()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || 'Upload failed')
  } finally {
    uploading.value = false
  }
}

async function handleDelete(filename) {
  await jarApi.deleteJar(serviceId.value, filename)
  ElMessage.success('JAR deleted')
  await loadJars()
}

onMounted(async () => {
  await loadService()
  await loadJars()
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
.subtitle {
  font-size: 13px;
  color: #909399;
}
</style>
