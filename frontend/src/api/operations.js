import request from './request'

export function getOperations(params) {
  return request.get('/operations', { params })
}

export function batchUpdateConfig(serviceIds, filename, content, dir = 'conf') {
  return request.post('/operations/batch/config', {
    service_ids: serviceIds,
    filename,
    content,
    dir,
  })
}

export function batchUploadJar(serviceIds, file) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('service_ids', JSON.stringify(serviceIds))
  return request.post('/operations/batch/jar', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
