<template>
  <div class="space-y-6">
    <!-- System Health Overview -->
    <Card>
      <CardHeader>
        <CardTitle class="flex items-center space-x-2">
          <Activity class="w-5 h-5" />
          <span>System Health Overview</span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <!-- CPU Usage -->
          <div class="space-y-2">
            <div class="flex justify-between items-center">
              <span class="text-sm font-medium">CPU Usage</span>
              <span class="text-sm text-gray-600">{{ cpuUsage }}%</span>
            </div>
            <Progress :value="cpuUsage" :class="getProgressClass(cpuUsage)" />
          </div>

          <!-- Memory Usage -->
          <div class="space-y-2">
            <div class="flex justify-between items-center">
              <span class="text-sm font-medium">Memory Usage</span>
              <span class="text-sm text-gray-600">{{ memoryUsage }}%</span>
            </div>
            <Progress :value="memoryUsage" :class="getProgressClass(memoryUsage)" />
          </div>

          <!-- Disk Usage -->
          <div class="space-y-2">
            <div class="flex justify-between items-center">
              <span class="text-sm font-medium">Disk Usage</span>
              <span class="text-sm text-gray-600">{{ diskUsage }}%</span>
            </div>
            <Progress :value="diskUsage" :class="getProgressClass(diskUsage)" />
          </div>
        </div>
      </CardContent>
    </Card>

    <!-- Performance Metrics -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <Card>
        <CardContent class="p-4">
          <div class="flex items-center space-x-2">
            <Globe class="w-4 h-4 text-blue-500" />
            <div>
              <p class="text-sm font-medium">Total Requests</p>
              <p class="text-2xl font-bold">{{ totalRequests }}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent class="p-4">
          <div class="flex items-center space-x-2">
            <Clock class="w-4 h-4 text-green-500" />
            <div>
              <p class="text-sm font-medium">Avg Response Time</p>
              <p class="text-2xl font-bold">{{ avgResponseTime }}ms</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent class="p-4">
          <div class="flex items-center space-x-2">
            <FileText class="w-4 h-4 text-purple-500" />
            <div>
              <p class="text-sm font-medium">Documents Processed</p>
              <p class="text-2xl font-bold">{{ documentsProcessed }}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent class="p-4">
          <div class="flex items-center space-x-2">
            <MessageSquare class="w-4 h-4 text-orange-500" />
            <div>
              <p class="text-sm font-medium">Queries Processed</p>
              <p class="text-2xl font-bold">{{ queriesProcessed }}</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>

    <!-- Error Summary -->
    <Card v-if="hasErrors">
      <CardHeader>
        <CardTitle class="flex items-center space-x-2 text-red-600">
          <AlertTriangle class="w-5 h-5" />
          <span>Error Summary</span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div class="space-y-2">
          <div v-for="(count, statusCode) in errorBreakdown" :key="statusCode" 
               class="flex justify-between items-center">
            <span class="text-sm">HTTP {{ statusCode }}</span>
            <Badge variant="destructive">{{ count }}</Badge>
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
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div class="text-center">
            <p class="text-2xl font-bold text-green-600">{{ cacheHits }}</p>
            <p class="text-sm text-gray-600">Cache Hits</p>
          </div>
          <div class="text-center">
            <p class="text-2xl font-bold text-red-600">{{ cacheMisses }}</p>
            <p class="text-sm text-gray-600">Cache Misses</p>
          </div>
          <div class="text-center">
            <p class="text-2xl font-bold text-blue-600">{{ cacheHitRate }}%</p>
            <p class="text-sm text-gray-600">Hit Rate</p>
          </div>
        </div>
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { 
  Activity, 
  Globe, 
  Clock, 
  FileText, 
  MessageSquare, 
  AlertTriangle, 
  Database 
} from 'lucide-vue-next'
import Card from '@/components/ui/Card.vue'
import CardContent from '@/components/ui/CardContent.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import Progress from '@/components/ui/Progress.vue'
import Badge from '@/components/ui/Badge.vue'

interface Props {
  healthData: any
  metricsData: any
  isLoading: boolean
}

const props = defineProps<Props>()

// Computed properties for system metrics
const cpuUsage = computed(() => 
  props.metricsData?.system?.cpu_percent?.toFixed(1) || 0
)

const memoryUsage = computed(() => 
  props.metricsData?.system?.memory_percent?.toFixed(1) || 0
)

const diskUsage = computed(() => 
  props.metricsData?.system?.disk_usage_percent?.toFixed(1) || 0
)

// Computed properties for application metrics
const totalRequests = computed(() => 
  props.metricsData?.application?.total_requests || 0
)

const avgResponseTime = computed(() => 
  (props.metricsData?.application?.avg_response_time * 1000)?.toFixed(0) || 0
)

const documentsProcessed = computed(() => 
  props.metricsData?.application?.documents_processed || 0
)

const queriesProcessed = computed(() => 
  props.metricsData?.application?.queries_processed || 0
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
  return total > 0 ? ((hits / total) * 100).toFixed(1) : 0
})

const errorBreakdown = computed(() => 
  props.metricsData?.error_breakdown || {}
)

const hasErrors = computed(() => 
  Object.keys(errorBreakdown.value).length > 0
)

// Helper methods
const getProgressClass = (value: number): string => {
  if (value >= 90) return 'text-red-500'
  if (value >= 75) return 'text-yellow-500'
  return 'text-green-500'
}
</script>