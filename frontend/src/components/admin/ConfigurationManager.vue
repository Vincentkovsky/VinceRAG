<template>
  <div class="space-y-6">
    <!-- Configuration Header -->
    <div class="flex items-center justify-between">
      <div>
        <h3 class="text-lg font-semibold">System Configuration</h3>
        <p class="text-sm text-gray-600 mt-1">
          Last reloaded: {{ formatTimestamp(configData?.last_reload) }}
        </p>
      </div>
      <div class="flex items-center space-x-2">
        <Badge :variant="configData?.hot_reload_enabled ? 'success' : 'secondary'">
          {{ configData?.hot_reload_enabled ? 'Hot Reload Enabled' : 'Hot Reload Disabled' }}
        </Badge>
        <Button @click="reloadConfig" :disabled="isLoading" size="sm">
          <RefreshCw class="w-4 h-4 mr-2" :class="{ 'animate-spin': isLoading }" />
          Reload Config
        </Button>
      </div>
    </div>

    <!-- Configuration Categories -->
    <div class="grid gap-6">
      <!-- Database Configuration -->
      <Card>
        <CardHeader>
          <CardTitle class="flex items-center space-x-2">
            <Database class="w-5 h-5" />
            <span>Database Configuration</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <ConfigItem 
              label="Database URL" 
              :value="getConfigValue('database_url')" 
              :sensitive="true" 
            />
            <ConfigItem 
              label="Pool Size" 
              :value="getConfigValue('database_pool_size')" 
            />
            <ConfigItem 
              label="Max Overflow" 
              :value="getConfigValue('database_max_overflow')" 
            />
            <ConfigItem 
              label="Redis URL" 
              :value="getConfigValue('redis_url')" 
              :sensitive="true" 
            />
          </div>
        </CardContent>
      </Card>

      <!-- API Configuration -->
      <Card>
        <CardHeader>
          <CardTitle class="flex items-center space-x-2">
            <Globe class="w-5 h-5" />
            <span>API Configuration</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <ConfigItem 
              label="Project Name" 
              :value="getConfigValue('project_name')" 
            />
            <ConfigItem 
              label="Debug Mode" 
              :value="getConfigValue('debug')" 
              :boolean="true" 
            />
            <ConfigItem 
              label="API Version" 
              :value="getConfigValue('api_v1_str')" 
            />
            <ConfigItem 
              label="CORS Origins" 
              :value="getConfigValue('backend_cors_origins')" 
              :array="true" 
            />
          </div>
        </CardContent>
      </Card>

      <!-- File Upload Configuration -->
      <Card>
        <CardHeader>
          <CardTitle class="flex items-center space-x-2">
            <Upload class="w-5 h-5" />
            <span>File Upload Configuration</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <ConfigItem 
              label="Max File Size" 
              :value="formatBytes(getConfigValue('max_file_size'))" 
            />
            <ConfigItem 
              label="Upload Directory" 
              :value="getConfigValue('upload_dir')" 
            />
          </div>
        </CardContent>
      </Card>

      <!-- Vector Database Configuration -->
      <Card>
        <CardHeader>
          <CardTitle class="flex items-center space-x-2">
            <Brain class="w-5 h-5" />
            <span>Vector Database Configuration</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <ConfigItem 
              label="Chroma Host" 
              :value="getConfigValue('chroma_host')" 
            />
            <ConfigItem 
              label="Chroma Port" 
              :value="getConfigValue('chroma_port')" 
            />
            <ConfigItem 
              label="Collection Name" 
              :value="getConfigValue('chroma_collection_name')" 
            />
            <ConfigItem 
              label="Persist Directory" 
              :value="getConfigValue('chroma_persist_directory')" 
            />
          </div>
        </CardContent>
      </Card>

      <!-- AI Configuration -->
      <Card>
        <CardHeader>
          <CardTitle class="flex items-center space-x-2">
            <Zap class="w-5 h-5" />
            <span>AI Configuration</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <ConfigItem 
              label="OpenAI API Key" 
              :value="getConfigValue('openai_api_key')" 
              :sensitive="true" 
            />
            <ConfigItem 
              label="Embedding Model" 
              :value="getConfigValue('openai_embedding_model')" 
            />
            <ConfigItem 
              label="Embedding Dimensions" 
              :value="getConfigValue('openai_embedding_dimensions')" 
            />
            <ConfigItem 
              label="Chunk Size" 
              :value="getConfigValue('chunk_size')" 
            />
          </div>
        </CardContent>
      </Card>

      <!-- Logging Configuration -->
      <Card>
        <CardHeader>
          <CardTitle class="flex items-center space-x-2">
            <FileText class="w-5 h-5" />
            <span>Logging Configuration</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <ConfigItem 
              label="Log Level" 
              :value="getConfigValue('log_level')" 
            />
            <ConfigItem 
              label="Structured Logging" 
              :value="getConfigValue('structured_logging')" 
              :boolean="true" 
            />
            <ConfigItem 
              label="Log File" 
              :value="getConfigValue('log_file')" 
            />
            <ConfigItem 
              label="Enable Metrics" 
              :value="getConfigValue('enable_metrics')" 
              :boolean="true" 
            />
          </div>
        </CardContent>
      </Card>

      <!-- Performance Configuration -->
      <Card>
        <CardHeader>
          <CardTitle class="flex items-center space-x-2">
            <Gauge class="w-5 h-5" />
            <span>Performance Configuration</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <ConfigItem 
              label="Request Timeout" 
              :value="getConfigValue('request_timeout') + 's'" 
            />
            <ConfigItem 
              label="Max Concurrent Requests" 
              :value="getConfigValue('max_concurrent_requests')" 
            />
            <ConfigItem 
              label="Health Check Interval" 
              :value="getConfigValue('health_check_interval') + 's'" 
            />
            <ConfigItem 
              label="Metrics Port" 
              :value="getConfigValue('metrics_port')" 
            />
          </div>
        </CardContent>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { 
  RefreshCw, 
  Database, 
  Globe, 
  Upload, 
  Brain, 
  Zap, 
  FileText, 
  Gauge 
} from 'lucide-vue-next'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card.vue'
import { Button } from '@/components/ui/Button.vue'
import { Badge } from '@/components/ui/Badge.vue'
import ConfigItem from './ConfigItem.vue'

interface ConfigData {
  last_reload: string
  hot_reload_enabled: boolean
  config_values: Record<string, any>
}

interface Props {
  configData: ConfigData | null
  isLoading: boolean
}

interface Emits {
  (e: 'reload-config'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// Methods
const reloadConfig = () => {
  emit('reload-config')
}

const getConfigValue = (key: string): any => {
  return props.configData?.config_values?.[key] || 'Not set'
}

const formatTimestamp = (timestamp: string | undefined): string => {
  if (!timestamp) return 'Never'
  const date = new Date(timestamp)
  return date.toLocaleString()
}

const formatBytes = (bytes: number): string => {
  if (!bytes) return '0 B'
  
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`
}
</script>