import axios, { type AxiosInstance, type InternalAxiosRequestConfig, type AxiosResponse } from 'axios'
import { useAppStore } from '@/stores/app'

// Create axios instance
const apiClient: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Add auth token if available
    const token = localStorage.getItem('auth_token')
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    
    // Add request timestamp for debugging
    ;(config as any).metadata = { startTime: new Date() }
    
    return config
  },
  (error) => {
    console.error('Request interceptor error:', error)
    return Promise.reject(error)
  }
)

// Response interceptor
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    // Log response time for debugging
    const endTime = new Date()
    const startTime = (response.config as any).metadata?.startTime
    if (startTime) {
      const duration = endTime.getTime() - startTime.getTime()
      console.debug(`API call to ${response.config.url} took ${duration}ms`)
    }
    
    return response
  },
  (error) => {
    const appStore = useAppStore()
    
    if (error.response) {
      // Server responded with error status
      const { status, data } = error.response
      
      switch (status) {
        case 401:
          // Unauthorized - clear token and redirect to login
          localStorage.removeItem('auth_token')
          appStore.addNotification({
            type: 'error',
            title: 'Authentication Error',
            message: 'Your session has expired. Please log in again.',
          })
          break
          
        case 403:
          // Forbidden
          appStore.addNotification({
            type: 'error',
            title: 'Access Denied',
            message: 'You do not have permission to perform this action.',
          })
          break
          
        case 404:
          // Not found
          appStore.addNotification({
            type: 'error',
            title: 'Not Found',
            message: 'The requested resource was not found.',
          })
          break
          
        case 422:
          // Validation error
          const validationMessage = data?.detail || 'Validation failed'
          appStore.addNotification({
            type: 'error',
            title: 'Validation Error',
            message: validationMessage,
          })
          break
          
        case 429:
          // Rate limit exceeded
          appStore.addNotification({
            type: 'warning',
            title: 'Rate Limit Exceeded',
            message: 'Too many requests. Please try again later.',
          })
          break
          
        case 500:
          // Internal server error
          appStore.addNotification({
            type: 'error',
            title: 'Server Error',
            message: 'An internal server error occurred. Please try again.',
          })
          break
          
        default:
          // Generic error
          const errorMessage = data?.message || `Request failed with status ${status}`
          appStore.addNotification({
            type: 'error',
            title: 'Request Failed',
            message: errorMessage,
          })
      }
    } else if (error.request) {
      // Network error
      appStore.addNotification({
        type: 'error',
        title: 'Network Error',
        message: 'Unable to connect to the server. Please check your connection.',
      })
    } else {
      // Other error
      appStore.addNotification({
        type: 'error',
        title: 'Error',
        message: error.message || 'An unexpected error occurred.',
      })
    }
    
    return Promise.reject(error)
  }
)

export default apiClient