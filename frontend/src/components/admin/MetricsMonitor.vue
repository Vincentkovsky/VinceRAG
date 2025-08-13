<template>
  <div class="space-y-6">
    <!-- Metrics Controls -->
    <div class="flex items-center justify-between">
      <h3 class="text-lg font-semibold">Performance Metrics</h3>
      <div class="flex items-center space-x-2">
        <Button @click="refreshMetrics" :disabled="isLoading" size="sm" variant="outline">
          <RefreshCw class="w-4 h-4 mr-2" :class="{ 'animate-spin': isLoading }" />
          Refresh
        </Button>
      </div>
    </div>

    <!-- Real-time Metrics Cards -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <!-- System Metrics -->
      <Card>
        <CardHeader class="pb-2">
          <CardTitle class="text-sm font-medium text-gray-600 flex items-center">
            <Cpu class="w-4 h-4 mr-2" />
            CPU Usage
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div class="space-y-2">
            <div class="text-2xl font-bold">{{ cpuUsage }}%</div>
            <Progress :value="parseFloat(cpuUsage)" :class="getUsageClass(parseFloat(cpuUsage))" />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader class="pb-2">
          <CardTitle class="text-sm font-medium text-gray-600 flex items-center">
            <MemoryStick class="w-4 h-4 mr-2" />
            Memory Usage
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div class="space-y-2">
            <div class="text-2xl font-bold">{{ memoryUsage }}%</div>
            <Progress :value="parseFloat(memoryUsage)" :class="getUsageClass(parseFloat(memoryUsage))" />
            <div class="text-xs text-gray-500">
              {{ formatBytes(metricsData?.system?.memory_used) }} / 
              {{ formatBytes(metricsData?.system?.memory_used + metricsData?.system?.memory_available) }}
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader class="pb-2">
          <CardTitle class="text-sm font-medium text-gray-600 flex items-center">
            <HardDrive class="w-4 h-4 mr-2" />
            Disk Usage
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div class="space-y-2">
            <div class="text-2xl font-bold">{{ diskUsage }}%</div>
            <Progress :value="parseFloat(diskUsage)" :class="getUsageClass(parseFloat(diskUsage))" />
            <div class="text-xs text-gray-500">
              {{ formatBytes(metricsData?.system?.disk_free) }} free
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader class="pb-2">
          <CardTitle class="text-sm font-medium text-gray-600 flex items-center">
            <Activity class="w-4 h-4 mr-2" />
            Active Requests
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div class="text-2xl font-bold">{{ activeRequests }}</div>
          <div class="text-xs text-gray-500 mt-1">
            {{ totalRequests }} total requests
          </div>
        </CardContent>
      </Card>
    </div>

    <!-- Application Metrics -->
    <Card>
      <CardHeader>
        <CardTitle class="flex items-center space-x-2">
          <BarChart3 class="w-5 h-5" />
          <span>Application Performance</span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div class="text-center">
            <div class="text-3xl font-bold text-blue-600">{{ avgResponseTime }}ms</div>
            <div class="text-sm text-gray-600">Avg Response Time</div>
          </div>
          
          <div class="text-center">
            <div class="text-3xl font-bold text-green-600">{{ documentsProcessed }}</div>
            <div class="text-sm text-gray-600">Documents Processed</div>
          </div>
          
          <div class="text-center">
            <div class="text-3xl font-bold text-purple-600">{{ queriesProcessed }}</div>
            <div class="text-sm text-gray-600">Queries Processed</div>
          </div>
          
          <div class="text-center">
            <div class="text-3xl font-bold text-orange-600">{{ vectorOperations }}</div>
            <div class="text-sm text-gray-600">Vector Operations</div>
          </div>
        </div>
      </CardContent>
    </Card>

    <!-- Network Activity -->
    <Card>
      <CardHeader>
        <CardTitle class="flex items-center space-x-2">
          <Wifi class="w-5 h-5" />
          <span>Network Activity</span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div class="text-center">
            <div class="text-2xl font-bold text-green-600">
              {{ formatBytes(metricsData?.system?.network_sent) }}
            </div>
            <div class="text-sm text-gray-600">Data Sent</div>
          </div>
          
          <div class="text-center">
            <div class="text-2xl font-bold text-blue-600">
              {{ formatBytes(metricsData?.system?.network_recv) }}
            </div>
            <div class="text-sm text-gray-600">Data Received</div>
          </div>
        </div>
      </CardContent>
    </Card>

    <!-- Cache Performance -->
    <Card>
      <CardHeader>
        <CardTitle class="flex items-center space-x-2">
          <Database class="w-5 h-5" />
          <span>Cache Performance</span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div class="text-center">
            <div class="text-2xl font-bold text-green-600">{{ cacheHits }}</div>
            <div class="text-sm text-gray-600">Cache Hits</div>
          </div>
          
          <div class="text-center">
            <div class="text-2xl font-bold text-red-600">{{ cacheMisses }}</div>
            <div class="text-sm text-gray-600">Cache Misses</div>
          </div>
          
          <div class="text-center">
            <div class="text-2xl font-bold text-blue-600">{{ cacheHitRate }}%</div>
            <div class="text-sm text-gray-600">Hit Rate</div>
            <Progress :value="parseFloat(cacheHitRate)" class="mt-2" />
          </div>
        </div>
      </CardContent>
    </Card>

    <!-- Error Breakdown -->
    <Card v-if="hasErrors">
      <CardHeader>
        <CardTitle class="flex items-center space-x-2 text-red-600">
          <AlertTriangle class="w-5 h-5" />
          <span>Error Breakdown</span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div v-for="(count, statusCode) in errorBreakdown" :key="statusCode" 
               class="text-center">
            <div class="text-xl font-bold text-red-600">{{ count }}</div>
            <div class="text-sm text-gray-600">HTTP {{ statusCode }}</div>
          </div>
        </div>
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { 
  RefreshCw, 
  Cpu, 
  MemoryStick, 
  HardDrive, 
  Activity, 
  BarChart3, 
  Wifi, 
  Database, 
  AlertTriangle 
} from 'lucide-vue-next'
import Card from '@/components/ui/Card.vue'
import CardContent from '@/components/ui/CardContent.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import Button from '@/components/ui/Button.vue'
import Progress from '@/components/ui/Progress.vue'

interface Props {
  metricsData: any
  metricsHistory: any
  isLoading: boolean
}

interface Emits {
  (e: 'refresh-metrics'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// Computed properties for system metrics
const cpuUsage = computed(() => 
  props.metricsData?.system?.cpu_percent?.toFixed(1) || '0'
)

const memoryUsage = computed(() => 
  props.metricsData?.system?.memory_percent?.toFixed(1) || '0'
)

const diskUsage = computed(() => 
  props.metricsData?.system?.disk_usage_percent?.toFixed(1) || '0'
)

// Computed properties for application metrics
const activeRequests = computed(() => 
  props.metricsData?.application?.active_requests || 0
)

const totalRequests = computed(() => 
  props.metricsData?.application?.total_requests || 0
)

const avgResponseTime = computed(() => 
  (props.metricsData?.application?.avg_response_time * 1000)?.toFixed(0) || '0'
)

const documentsProcessed = computed(() => 
  props.metricsData?.application?.documents_processed || 0
)

const queriesProcessed = computed(() => 
  props.metricsData?.application?.queries_processed || 0
)

const vectorOperations = computed(() => 
  props.metricsData?.application?.vector_operations || 0
)

const cacheHits = computed(() => 
  props.metricsData?.application?.cache_hits || 0
)

const cacheMisses = computed(() => 
  props.metricsData?.application?.cache_misses || 0
)

const cacheHitRate = computed(() => {
  const hits = cacheHits.value
  const misses = cacheMisses.value
  const total = hits + misses
  return total > 0 ? ((hits / total) * 100).toFixed(1) : '0'
})

const errorBreakdown = computed(() => 
  props.metricsData?.error_breakdown || {}
)

const hasErrors = computed(() => 
  Object.keys(errorBreakdown.value).length > 0
)

// Methods
const refreshMetrics = () => {
  emit('refresh-metrics')
}

const getUsageClass = (value: number): string => {
  if (value >= 90) return 'text-red-500'
  if (value >= 75) return 'text-yellow-500'
  return 'text-green-500'
}

const formatBytes = (bytes: number): string => {
  if (!bytes) return '0 B'
  
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`
}
</script>