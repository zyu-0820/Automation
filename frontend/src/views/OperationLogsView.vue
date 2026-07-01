<template>
  <div class="operations-view">
    <h2>Operation Logs</h2>

    <el-form inline style="margin-bottom: 16px">
      <el-form-item label="Server">
        <el-select v-model="filterServerId" clearable placeholder="All" style="min-width: 200px" @change="loadLogs">
          <el-option v-for="s in serverStore.servers" :key="s.id" :label="s.name" :value="s.id" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button @click="loadLogs">Refresh</el-button>
      </el-form-item>
    </el-form>

    <el-table :data="logs" stripe v-loading="loading">
      <el-table-column label="Time" width="180">
        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column prop="operation_type" label="Operation" width="140">
        <template #default="{ row }">
          <el-tag size="small">{{ row.operation_type }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="target_file" label="Target File" min-width="200" show-overflow-tooltip />
      <el-table-column prop="backup_file" label="Backup" min-width="200" show-overflow-tooltip />
      <el-table-column prop="status" label="Status" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 'success' ? 'success' : 'danger'" size="small">
            {{ row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="message" label="Message" min-width="150" show-overflow-tooltip />
    </el-table>

    <div class="pagination" style="margin-top: 16px; text-align: right">
      <el-pagination
        v-model:current-page="page"
        :page-size="50"
        layout="prev, pager, next"
        :total="total"
        @current-change="loadLogs"
      />
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useServerStore } from '@/stores/server'
import * as operationApi from '@/api/operations'
import { formatDateTime } from '@/utils/helpers'

const serverStore = useServerStore()
const logs = ref([])
const loading = ref(false)
const page = ref(1)
const total = ref(0)
const filterServerId = ref(null)

async function loadLogs() {
  loading.value = true
  try {
    const params = { skip: (page.value - 1) * 50, limit: 50 }
    if (filterServerId.value) params.server_id = filterServerId.value
    const { data } = await operationApi.getOperations(params)
    logs.value = data
    total.value = data.length >= 50 ? (page.value * 50 + 1) : page.value * 50
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  serverStore.fetchServers()
  loadLogs()
})
</script>
