import { ref } from 'vue'
import { defineStore } from 'pinia'
import * as serviceApi from '@/api/services'

export const useServiceStore = defineStore('service', () => {
  const services = ref([])
  const loading = ref(false)

  async function fetchServices(serverId) {
    loading.value = true
    try {
      const { data } = await serviceApi.getServices(serverId)
      services.value = data
    } finally {
      loading.value = false
    }
  }

  async function scanServices(serverId) {
    const { data } = await serviceApi.scanServices(serverId)
    return data
  }

  async function refreshStatus(serviceId) {
    const { data } = await serviceApi.refreshStatus(serviceId)
    return data
  }

  async function deleteService(serviceId) {
    await serviceApi.deleteService(serviceId)
  }

  return { services, loading, fetchServices, scanServices, refreshStatus, deleteService }
})
