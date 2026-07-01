import request from './request'

export function getJars(serviceId) {
  return request.get(`/services/${serviceId}/jars`)
}

export function uploadJar(serviceId, file) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post(`/services/${serviceId}/jars/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function deleteJar(serviceId, filename) {
  return request.delete(`/services/${serviceId}/jars/${encodeURIComponent(filename)}`)
}
