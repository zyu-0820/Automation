import request from './request'

export function getServices(serverId) {
  return request.get(`/servers/${serverId}/services`)
}

export function createService(serverId, data) {
  return request.post(`/servers/${serverId}/services`, data)
}

export function scanServices(serverId) {
  return request.post(`/servers/${serverId}/services/scan`)
}

export function getService(id) {
  return request.get(`/services/${id}`)
}

export function deleteService(id) {
  return request.delete(`/services/${id}`)
}

export function refreshStatus(id) {
  return request.post(`/services/${id}/refresh-status`)
}

export function startService(id) {
  return request.post(`/services/${id}/start`)
}

export function stopService(id) {
  return request.post(`/services/${id}/stop`)
}

export function restartService(id) {
  return request.post(`/services/${id}/restart`)
}

export function updateService(id, data) {
  return request.put(`/services/${id}`, data)
}

export function refreshAllStatus(serverId) {
  return request.post(`/servers/${serverId}/services/refresh-all`)
}
