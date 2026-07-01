import { ref } from 'vue'
import { defineStore } from 'pinia'
import * as serverApi from '@/api/servers'

export const useServerStore = defineStore('server', () => {
  const servers = ref([])
  const loading = ref(false)

  async function fetchServers() {
    loading.value = true
    try {
      const { data } = await serverApi.getServers()
      servers.value = data
    } finally {
      loading.value = false
    }
  }

  async function createServer(form) {
    const { data } = await serverApi.createServer(form)
    await fetchServers()
    return data
  }

  async function updateServer(id, form) {
    const { data } = await serverApi.updateServer(id, form)
    await fetchServers()
    return data
  }

  async function deleteServer(id) {
    await serverApi.deleteServer(id)
    await fetchServers()
  }

  async function testConnection(id) {
    const { data } = await serverApi.testConnection(id)
    return data
  }

  return { servers, loading, fetchServers, createServer, updateServer, deleteServer, testConnection }
})
