<template>
  <div class="admin-dashboard p-6 space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-gray-900">Admin Dashboard</h1>
        <p class="text-gray-600 mt-1">System monitoring and administration</p>
      </div>
      <div class="flex items-center space-x-4">
        <Badge :variant="systemStatus.variant" class="text-sm">
          {{ systemStatus.text }}
        </Badge>
        <Button @click="refreshData" :disabled="isLoading" size="sm">
          <RefreshCw class="w-4 h-4 mr-2" :class="{ 'animate-spin': isLoading }" />
          Refresh
        </Button>
      </div>
    </div>

    <!-- System Status Cards -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <Card>
        <CardHeader class="pb-2">
          <CardTitle class="text-sm font-medium text-gray-600">System Status</CardTitle>
        </CardHeader>
        <CardContent>
          <div class="flex items-center space-x-2">
            <div :class="statusIndicatorClass" class="w-3 h-3 rounded-full"></div>
            <span class="text-2xl font-bold">{{ healthData?.status || 'Unknown' }}</span>
          </div>
          <p class="text-sm text-gray-600 mt-1">
            {{ healthData?.summary?.healthy || 0 }}/{{ healthData?.summary?.total_components || 0 }} components healthy
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader class="pb-2">
          <CardTitle class="text-sm font-medium text-gray-600">Uptime</CardTitle>
        </CardHeader>
        <CardContent>
          <div class="text-2xl font-bold">{{ formatUptime(metricsData?.uptime_seconds) }}</div>
          <p class="text-sm text-gray-600 mt-1">System running</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader class="pb-2">
          <CardTitle class="text-sm font-medium text-gray-600">Active Requests</CardTitle>
        </CardHeader>
        <CardContent>
          <div class="text-2xl font-bold">{{ metricsData?.application?.active_requests || 0 }}</div>
          <p class="text-sm text-gray-600 mt-1">Current connections</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader class="pb-2">
          <CardTitle class="text-sm font-medium text-gray-600">Memory Usage</CardTitle>
        </CardHeader>
        <CardContent>
          <div class="text-2xl font-bold">{{ metricsData?.system?.memory_percent?.toFixed(1) || 0 }}%</div>
          <Progress :value="metricsData?.system?.memory_percent || 0" class="mt-2" />
        </CardContent>
      </Card>
    </div>

    <!-- Tabs for different sections -->
    <Tabs v-model="activeTab" class="w-full">
      <TabsList class="grid w-full grid-cols-6">
        <TabsTrigger value="overview">Overview</TabsTrigger>
        <TabsTrigger value="components">Components</TabsTrigger>
        <TabsTrigger value="metrics">Metrics</TabsTrigger>
        <TabsTrigger value="logs">Logs</TabsTrigger>
        <TabsTrigger value="config">Configuration</TabsTrigger>
        <TabsTrigger value="models">AI Models</TabsTrigger>
      </TabsList>

      <!-- Overview Tab -->
      <TabsContent value="overview" class="space-y-6">
        <SystemOverview 
          :health-data="healthData" 
          :metrics-data="metricsData"
          :is-loading="isLoading"
        />
      </TabsContent>

      <!-- Components Tab -->
      <TabsContent value="components" class="space-y-6">
        <ComponentsMonitor 
          :components="healthData?.components || []"
          :is-loading="isLoading"
          @refresh-component="refreshComponent"
        />
      </TabsContent>

      <!-- Metrics Tab -->
      <TabsContent value="metrics" class="space-y-6">
        <MetricsMonitor 
          :metrics-data="metricsData"
          :metrics-history="metricsHistory"
          :is-loading="isLoading"
          @refresh-metrics="refreshMetrics"
        />
      </TabsContent>

      <!-- Logs Tab -->
      <TabsContent value="logs" class="space-y-6">
        <LogsViewer 
          :logs="logsData"
          :is-loading="isLoading"
          @refresh-logs="refreshLogs"
          @filter-logs="filterLogs"
        />
      </TabsContent>

      <!-- Configuration Tab -->
      <TabsContent value="config" class="space-y-6">
        <ConfigurationManager 
          :config-data="configData"
          :is-loading="isLoading"
          @reload-config="reloadConfiguration"
        />
      </TabsContent>

      <!-- AI Models Tab -->
      <TabsContent value="models" class="space-y-6">
        <ModelConfiguration />
      </TabsContent>
    </Tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { RefreshCw } from 'lucide-vue-next'
import Card from '@/components/ui/Card.vue'
import CardContent from '@/components/ui/CardContent.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import Progress from '@/components/ui/Progress.vue'
import Tabs from '@/components/ui/Tabs.vue'
import TabsContent from '@/components/ui/TabsContent.vue'
import TabsList from '@/components/ui/TabsList.vue'
import TabsTrigger from '@/components/ui/TabsTrigger.vue'
import SystemOverview from '@/components/admin/SystemOverview.vue'
import ComponentsMonitor from '@/components/admin/ComponentsMonitor.vue'
import MetricsMonitor from '@/components/admin/MetricsMonitor.vue'
import LogsViewer from '@/components/admin/LogsViewer.vue'
import ConfigurationManager from '@/components/admin/ConfigurationManager.vue'
import ModelConfiguration from '@/components/admin/ModelConfiguration.vue'
import { adminApi } from '@/api/admin'

// Reactive state
const isLoading = ref(false)
const activeTab = ref('overview')
const healthData = ref<any>(null)
const metricsData = ref<any>(null)
const metricsHistory = ref<any>(null)
const logsData = ref<any>(null)
const configData = ref<any>(null)

// Auto-refresh interval
let refreshInterval: NodeJS.Timeout | null = null

// Computed properties
const systemStatus = computed(() => {
  const status = healthData.value?.status
  switch (status) {
    case 'healthy':
      return { text: 'Healthy', variant: 'success' as const }
    case 'degraded':
      return { text: 'Degraded', variant: 'warning' as const }
    case 'unhealthy':
      return { text: 'Unhealthy', variant: 'destructive' as const }
    default:
      return { text: 'Unknown', variant: 'secondary' as const }
  }
})

const statusIndicatorClass = computed(() => {
  const status = healthData.value?.status
  switch (status) {
    case 'healthy':
      return 'bg-green-500'
    case 'degraded':
      return 'bg-yellow-500'
    case 'unhealthy':
      return 'bg-red-500'
    default:
      return 'bg-gray-500'
  }
})

// Methods
const formatUptime = (seconds: number): string => {
  if (!seconds) return '0s'
  
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  
  if (days > 0) return `${days}d ${hours}h`
  if (hours > 0) return `${hours}h ${minutes}m`
  return `${minutes}m`
}

const refreshData = async () => {
  isLoading.value = true
  try {
    await Promise.all([
      refreshHealth(),
      refreshMetrics(),
      refreshConfiguration()
    ])
  } finally {
    isLoading.value = false
  }
}

const refreshHealth = async () => {
  try {
    healthData.value = await adminApi.getSystemStatus()
  } catch (error) {
    console.error('Failed to fetch health data:', error)
  }
}

const refreshMetrics = async () => {
  try {
    const [current, history] = await Promise.all([
      adminApi.getMetrics(),
      adminApi.getMetricsHistory(1) // Last 1 hour
    ])
    metricsData.value = current
    metricsHistory.value = history
  } catch (error) {
    console.error('Failed to fetch metrics:', error)
  }
}

const refreshConfiguration = async () => {
  try {
    configData.value = await adminApi.getConfiguration()
  } catch (error) {
    console.error('Failed to fetch configuration:', error)
  }
}

const refreshComponent = async (componentName: string) => {
  try {
    const componentHealth = await adminApi.getComponentHealth(componentName)
    // Update the specific component in healthData
    if (healthData.value?.components) {
      const index = healthData.value.components.findIndex((c: any) => c.name === componentName)
      if (index !== -1) {
        healthData.value.components[index] = componentHealth
      }
    }
  } catch (error) {
    console.error(`Failed to refresh component ${componentName}:`, error)
  }
}

const refreshLogs = async (filters = {}) => {
  try {
    logsData.value = await adminApi.getLogs(filters)
  } catch (error) {
    console.error('Failed to fetch logs:', error)
  }
}

const filterLogs = async (filters: any) => {
  await refreshLogs(filters)
}

const reloadConfiguration = async () => {
  try {
    await adminApi.reloadConfiguration()
    await refreshConfiguration()
  } catch (error) {
    console.error('Failed to reload configuration:', error)
  }
}

// Lifecycle
onMounted(() => {
  refreshData()
  
  // Set up auto-refresh every 30 seconds
  refreshInterval = setInterval(() => {
    refreshHealth()
    refreshMetrics()
  }, 30000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>