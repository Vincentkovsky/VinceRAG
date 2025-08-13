<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h3 class="text-lg font-semibold">System Components</h3>
      <Button @click="refreshAll" :disabled="isLoading" size="sm">
        <RefreshCw class="w-4 h-4 mr-2" :class="{ 'animate-spin': isLoading }" />
        Refresh All
      </Button>
    </div>

    <div class="grid gap-4">
      <Card v-for="component in components" :key="component.name">
        <CardContent class="p-4">
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-3">
              <div :class="getStatusIndicatorClass(component.status)" 
                   class="w-3 h-3 rounded-full"></div>
              <div>
                <h4 class="font-medium capitalize">{{ formatComponentName(component.name) }}</h4>
                <p class="text-sm text-gray-600">{{ component.message }}</p>
              </div>
            </div>
            
            <div class="flex items-center space-x-3">
              <div class="text-right">
                <Badge :variant="getStatusVariant(component.status)">
                  {{ component.status }}
                </Badge>
                <p v-if="component.response_time" class="text-xs text-gray-500 mt-1">
                  {{ (component.response_time * 1000).toFixed(0) }}ms
                </p>
              </div>
              
              <Button 
                @click="refreshComponent(component.name)" 
                size="sm" 
                variant="outline"
                :disabled="refreshingComponents.has(component.name)"
              >
                <RefreshCw class="w-4 h-4" 
                          :class="{ 'animate-spin': refreshingComponents.has(component.name) }" />
              </Button>
            </div>
          </div>

          <!-- Component Details -->
          <Collapsible v-if="component.details && Object.keys(component.details).length > 0">
            <CollapsibleTrigger class="flex items-center space-x-2 mt-3 text-sm text-gray-600 hover:text-gray-900">
              <ChevronRight class="w-4 h-4 transition-transform" />
              <span>View Details</span>
            </CollapsibleTrigger>
            <CollapsibleContent class="mt-2">
              <div class="bg-gray-50 rounded-lg p-3 space-y-2">
                <div v-for="(value, key) in component.details" :key="key" 
                     class="flex justify-between items-center text-sm">
                  <span class="font-medium capitalize">{{ formatDetailKey(key) }}:</span>
                  <span class="text-gray-600">{{ formatDetailValue(value) }}</span>
                </div>
              </div>
            </CollapsibleContent>
          </Collapsible>

          <!-- Last Updated -->
          <div class="mt-3 text-xs text-gray-500">
            Last checked: {{ formatTimestamp(component.timestamp) }}
          </div>
        </CardContent>
      </Card>
    </div>

    <!-- Empty State -->
    <div v-if="components.length === 0" class="text-center py-8">
      <Server class="w-12 h-12 text-gray-400 mx-auto mb-4" />
      <p class="text-gray-600">No component data available</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { 
  RefreshCw, 
  ChevronRight, 
  Server 
} from 'lucide-vue-next'
import { Card, CardContent } from '@/components/ui/Card.vue'
import { Button } from '@/components/ui/Button.vue'
import { Badge } from '@/components/ui/Badge.vue'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/Collapsible.vue'

interface ComponentHealth {
  name: string
  status: 'healthy' | 'degraded' | 'unhealthy'
  message: string
  response_time?: number
  details?: Record<string, any>
  timestamp: string
}

interface Props {
  components: ComponentHealth[]
  isLoading: boolean
}

interface Emits {
  (e: 'refresh-component', componentName: string): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const refreshingComponents = ref(new Set<string>())

// Methods
const refreshAll = () => {
  props.components.forEach(component => {
    refreshComponent(component.name)
  })
}

const refreshComponent = async (componentName: string) => {
  refreshingComponents.value.add(componentName)
  try {
    emit('refresh-component', componentName)
    // Remove from refreshing set after a delay to show the animation
    setTimeout(() => {
      refreshingComponents.value.delete(componentName)
    }, 1000)
  } catch (error) {
    refreshingComponents.value.delete(componentName)
  }
}

const getStatusIndicatorClass = (status: string): string => {
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
}

const getStatusVariant = (status: string): string => {
  switch (status) {
    case 'healthy':
      return 'success'
    case 'degraded':
      return 'warning'
    case 'unhealthy':
      return 'destructive'
    default:
      return 'secondary'
  }
}

const formatComponentName = (name: string): string => {
  return name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

const formatDetailKey = (key: string): string => {
  return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

const formatDetailValue = (value: any): string => {
  if (typeof value === 'number') {
    if (value > 1000000) {
      return `${(value / 1000000).toFixed(1)}M`
    } else if (value > 1000) {
      return `${(value / 1000).toFixed(1)}K`
    }
    return value.toString()
  }
  if (typeof value === 'boolean') {
    return value ? 'Yes' : 'No'
  }
  return String(value)
}

const formatTimestamp = (timestamp: string): string => {
  const date = new Date(timestamp)
  return date.toLocaleString()
}
</script>