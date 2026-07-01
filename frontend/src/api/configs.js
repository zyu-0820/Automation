import request from './request'

export function getConfigFiles(serviceId, ext) {
  return request.get(`/services/${serviceId}/configs`, { params: ext ? { ext } : {} })
}

export function getConfigContent(serviceId, filename, dir = 'conf') {
  return request.get(`/services/${serviceId}/configs/${encodeURIComponent(filename)}`, {
    params: { dir },
  })
}

export function updateConfig(serviceId, filename, content, dir = 'conf') {
  return request.put(`/services/${serviceId}/configs/${encodeURIComponent(filename)}`, {
    content,
    dir,
  })
}
