/**
 * Admin API client for system monitoring and configuration
 */

import { apiClient } from './client'

export interface HealthData {
  status: 'healthy' | 'degraded' | 'unhealthy'
  timestamp: string
  components: ComponentHealth[]
  summary: {
    total_components: number
    healthy: number
    degraded: number
    unhealthy: number
  }
}

export interface ComponentHealth {
  name: string
  status: 'healthy' | 'degraded' | 'unhealthy'
  message: string
  response_time?: number
  details?: Record<string, any>
  timestamp: string
}

export interface MetricsData {
  system: {
    cpu_percent: number
    memory_percent: number
    memory_used: number
    memory_available: number
    disk_usage_percent: number
    disk_free: number
    network_sent: number
    network_recv: number
    timestamp: string
  }
  application: {
    active_requests: number
    total_requests: number
    error_count: number
    avg_response_time: number
    documents_processed: number
    queries_processed: number
    vector_operations: number
    cache_hits: number
    cache_misses: number
    timestamp: string
  }
  uptime_seconds: number
  error_breakdown: Record<string, number>
}

export interface LogEntry {
  timestamp: string
  level: string
  logger: string
  message: string
  module?: string
  function?: string
  line?: number
  request_id?: string
  user_id?: string
  [key: string]: any
}

export interface ConfigData {
  last_reload: string
  hot_reload_enabled: boolean
  config_values: Record<string, any>
}

export interface LogsResponse {
  logs: LogEntry[]
  total: number
  filters: {
    level?: string
    component?: string
    limit: number
  }
}

export const adminApi = {
  /**
   * Get comprehensive system status
   */
  async getSystemStatus(): Promise<HealthData> {
    const response = await apiClient.get('/admin/status')
    return response.data
  },

  /**
   * Get basic health check
   */
  async getHealthCheck(): Promise<HealthData> {
    const response = await apiClient.get('/admin/health')
    return response.data
  },

  /**
   * Get health status for a specific component
   */
  async getComponentHealth(component: string): Promise<ComponentHealth> {
    const response = await apiClient.get(`/admin/health/${component}`)
    return response.data
  },

  /**
   * Get current system metrics
   */
  async getMetrics(): Promise<MetricsData> {
    const response = await apiClient.get('/admin/metrics')
    return response.data
  },

  /**
   * Get metrics history
   */
  async getMetricsHistory(hours: number = 1): Promise<any> {
    const response = await apiClient.get('/admin/metrics/history', {
      params: { hours }
    })
    return response.data
  },

  /**
   * Get system configuration
   */
  async getConfiguration(): Promise<ConfigData> {
    const response = await apiClient.get('/admin/config')
    return response.data
  },

  /**
   * Reload system configuration
   */
  async reloadConfiguration(): Promise<{ message: string; changes: Record<string, any> }> {
    const response = await apiClient.post('/admin/config/reload')
    return response.data
  },

  /**
   * Get recent log entries
   */
  async getLogs(filters: {
    level?: string
    component?: string
    limit?: number
  } = {}): Promise<LogsResponse> {
    const response = await apiClient.get('/admin/logs', {
      params: {
        level: filters.level,
        component: filters.component,
        limit: filters.limit || 100
      }
    })
    return response.data
  },

  /**
   * Trigger garbage collection
   */
  async triggerGarbageCollection(): Promise<{ message: string; objects_collected: number }> {
    const response = await apiClient.post('/admin/maintenance/gc')
    return response.data
  },

  /**
   * Get system information
   */
  async getSystemInfo(): Promise<{
    application: Record<string, any>
    system: Record<string, any>
    runtime: Record<string, any>
  }> {
    const response = await apiClient.get('/admin/info')
    return response.data
  }
}