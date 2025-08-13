<template>
  <div class="space-y-4">
    <!-- Logs Controls -->
    <div class="flex items-center justify-between">
      <h3 class="text-lg font-semibold">System Logs</h3>
      <div class="flex items-center space-x-2">
        <Button @click="refreshLogs" :disabled="isLoading" size="sm" variant="outline">
          <RefreshCw class="w-4 h-4 mr-2" :class="{ 'animate-spin': isLoading }" />
          Refresh
        </Button>
      </div>
    </div>

    <!-- Filters -->
    <Card>
      <CardContent class="p-4">
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label class="text-sm font-medium mb-2 block">Log Level</label>
            <select 
              v-model="filters.level" 
              @change="applyFilters"
              class="w-full p-2 border rounded-md text-sm"
            >
              <option value="">All Levels</option>
              <option value="DEBUG">Debug</option>
              <option value="INFO">Info</option>
              <option value="WARNING">Warning</option>
              <option value="ERROR">Error</option>
              <option value="CRITICAL">Critical</option>
            </select>
          </div>

          <div>
            <label class="text-sm font-medium mb-2 block">Component</label>
            <select 
              v-model="filters.component" 
              @change="applyFilters"
              class="w-full p-2 border rounded-md text-sm"
            >
              <option value="">All Components</option>
              <option value="main">Main</option>
              <option value="api">API</option>
              <option value="services">Services</option>
              <option value="middleware">Middleware</option>
              <option value="database">Database</option>
            </select>
          </div>

          <div>
            <label class="text-sm font-medium mb-2 block">Limit</label>
            <select 
              v-model="filters.limit" 
              @change="applyFilters"
              class="w-full p-2 border rounded-md text-sm"
            >
              <option :value="50">50 entries</option>
              <option :value="100">100 entries</option>
              <option :value="200">200 entries</option>
              <option :value="500">500 entries</option>
            </select>
          </div>

          <div class="flex items-end">
            <Button @click="clearFilters" variant="outline" size="sm" class="w-full">
              Clear Filters
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>

    <!-- Logs Display -->
    <Card>
      <CardHeader>
        <CardTitle class="flex items-center justify-between">
          <span class="flex items-center space-x-2">
            <FileText class="w-5 h-5" />
            <span>Log Entries</span>
          </span>
          <Badge variant="secondary">{{ logs?.total || 0 }} entries</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent class="p-0">
        <div class="max-h-96 overflow-y-auto">
          <div v-if="logs?.logs?.length === 0" class="p-8 text-center text-gray-500">
            <FileText class="w-12 h-12 mx-auto mb-4 text-gray-300" />
            <p>No log entries found</p>
            <p class="text-sm mt-1">Try adjusting your filters or check if file logging is enabled</p>
          </div>

          <div v-else class="divide-y">
            <div 
              v-for="(log, index) in logs?.logs" 
              :key="index"
              class="p-4 hover:bg-gray-50 transition-colors"
            >
              <div class="flex items-start space-x-3">
                <!-- Log Level Badge -->
                <Badge :variant="getLogLevelVariant(log.level)" class="mt-0.5 text-xs">
                  {{ log.level }}
                </Badge>

                <!-- Log Content -->
                <div class="flex-1 min-w-0">
                  <div class="flex items-center space-x-2 mb-1">
                    <span class="text-sm font-medium text-gray-900">{{ log.logger }}</span>
                    <span class="text-xs text-gray-500">{{ formatTimestamp(log.timestamp) }}</span>
                    <span v-if="log.request_id" class="text-xs text-blue-600 bg-blue-50 px-2 py-0.5 rounded">
                      {{ log.request_id.substring(0, 8) }}
                    </span>
                  </div>

                  <p class="text-sm text-gray-800 mb-2">{{ log.message }}</p>

                  <!-- Additional Context -->
                  <div v-if="hasAdditionalContext(log)" class="text-xs text-gray-600 space-y-1">
                    <div v-if="log.module" class="flex items-center space-x-2">
                      <span class="font-medium">Module:</span>
                      <span>{{ log.module }}.{{ log.function }}:{{ log.line }}</span>
                    </div>
                    
                    <div v-if="log.user_id" class="flex items-center space-x-2">
                      <span class="font-medium">User:</span>
                      <span>{{ log.user_id }}</span>
                    </div>

                    <!-- Custom context data -->
                    <div v-if="log.context" class="mt-2">
                      <Collapsible>
                        <CollapsibleTrigger class="flex items-center space-x-1 text-blue-600 hover:text-blue-800">
                          <ChevronRight class="w-3 h-3 transition-transform" />
                          <span>View Context</span>
                        </CollapsibleTrigger>
                        <CollapsibleContent class="mt-1">
                          <pre class="bg-gray-100 p-2 rounded text-xs overflow-x-auto">{{ JSON.stringify(log.context, null, 2) }}</pre>
                        </CollapsibleContent>
                      </Collapsible>
                    </div>

                    <!-- Exception info -->
                    <div v-if="log.exception" class="mt-2">
                      <Collapsible>
                        <CollapsibleTrigger class="flex items-center space-x-1 text-red-600 hover:text-red-800">
                          <ChevronRight class="w-3 h-3 transition-transform" />
                          <span>View Exception</span>
                        </CollapsibleTrigger>
                        <CollapsibleContent class="mt-1">
                          <div class="bg-red-50 p-2 rounded text-xs">
                            <div class="font-medium text-red-800">{{ log.exception.type }}: {{ log.exception.message }}</div>
                            <pre class="mt-1 text-red-700 overflow-x-auto">{{ log.exception.traceback }}</pre>
                          </div>
                        </CollapsibleContent>
                      </Collapsible>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import { RefreshCw, FileText, ChevronRight } from 'lucide-vue-next'
import Card from '@/components/ui/Card.vue'
import CardContent from '@/components/ui/CardContent.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import Collapsible from '@/components/ui/Collapsible.vue'
import CollapsibleContent from '@/components/ui/CollapsibleContent.vue'
import CollapsibleTrigger from '@/components/ui/CollapsibleTrigger.vue'

interface LogEntry {
  timestamp: string
  level: string
  logger: string
  message: string
  module?: string
  function?: string
  line?: number
  request_id?: string
  user_id?: string
  context?: any
  exception?: {
    type: string
    message: string
    traceback: string
  }
  [key: string]: any
}

interface LogsResponse {
  logs: LogEntry[]
  total: number
  filters: {
    level?: string
    component?: string
    limit: number
  }
}

interface Props {
  logs: LogsResponse | null
  isLoading: boolean
}

interface Emits {
  (e: 'refresh-logs'): void
  (e: 'filter-logs', filters: any): void
}

defineProps<Props>()
const emit = defineEmits<Emits>()

const filters = reactive({
  level: '',
  component: '',
  limit: 100
})

// Methods
const refreshLogs = () => {
  emit('refresh-logs')
}

const applyFilters = () => {
  emit('filter-logs', { ...filters })
}

const clearFilters = () => {
  filters.level = ''
  filters.component = ''
  filters.limit = 100
  applyFilters()
}

const getLogLevelVariant = (level: string): 'secondary' | 'default' | 'warning' | 'destructive' => {
  switch (level.toUpperCase()) {
    case 'DEBUG':
      return 'secondary'
    case 'INFO':
      return 'default'
    case 'WARNING':
      return 'warning'
    case 'ERROR':
      return 'destructive'
    case 'CRITICAL':
      return 'destructive'
    default:
      return 'secondary'
  }
}

const formatTimestamp = (timestamp: string): string => {
  const date = new Date(timestamp)
  return date.toLocaleString()
}

const hasAdditionalContext = (log: LogEntry): boolean => {
  return !!(log.module || log.user_id || log.context || log.exception)
}
</script>