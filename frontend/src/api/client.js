import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 30000,
})
api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('scout_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && !error.config?.url?.startsWith('/auth/')) {
      sessionStorage.removeItem('scout_token')
      window.dispatchEvent(new Event('scout:unauthorized'))
    }
    return Promise.reject(error)
  },
)
export function errorMessage(error) {
  const detail = error.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail))
    return detail.map((item) => `${item.loc.at(-1)}: ${item.msg}`).join('; ')
  return error.code === 'ECONNABORTED'
    ? 'The request timed out. Please try again.'
    : 'Cannot reach ScoutAI. Check your connection and try again.'
}
