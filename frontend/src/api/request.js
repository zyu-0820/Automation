import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

request.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail = error.response?.data?.detail
    const msg = detail?.message || error.message || 'Request failed'
    ElMessage.error(msg)
    return Promise.reject(error)
  }
)

export default request
