<template>
  <div class="space-y-1">
    <label class="text-sm font-medium text-gray-700">{{ label }}</label>
    <div class="text-sm text-gray-900">
      <!-- Boolean values -->
      <Badge v-if="boolean" :variant="value ? 'success' : 'secondary'">
        {{ value ? 'Enabled' : 'Disabled' }}
      </Badge>
      
      <!-- Array values -->
      <div v-else-if="array" class="space-y-1">
        <Badge v-for="item in (Array.isArray(value) ? value : [])" :key="item" variant="outline" class="mr-1">
          {{ item }}
        </Badge>
        <span v-if="!Array.isArray(value) || value.length === 0" class="text-gray-500 italic">
          None configured
        </span>
      </div>
      
      <!-- Sensitive values -->
      <div v-else-if="sensitive" class="flex items-center space-x-2">
        <span v-if="showSensitive">{{ value }}</span>
        <span v-else class="text-gray-500">{{ maskSensitiveValue(value) }}</span>
        <Button 
          @click="toggleSensitive" 
          size="sm" 
          variant="ghost" 
          class="h-6 w-6 p-0"
        >
          <Eye v-if="!showSensitive" class="w-3 h-3" />
          <EyeOff v-else class="w-3 h-3" />
        </Button>
      </div>
      
      <!-- Regular values -->
      <span v-else :class="getValueClass()">
        {{ formatValue(value) }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Eye, EyeOff } from 'lucide-vue-next'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'

interface Props {
  label: string
  value: any
  sensitive?: boolean
  boolean?: boolean
  array?: boolean
}

const props = defineProps<Props>()

const showSensitive = ref(false)

// Methods
const toggleSensitive = () => {
  showSensitive.value = !showSensitive.value
}

const maskSensitiveValue = (value: any): string => {
  if (!value || value === 'Not set') return 'Not set'
  if (typeof value === 'string' && value.length > 8) {
    return value.substring(0, 4) + '***' + value.substring(value.length - 4)
  }
  return '***'
}

const formatValue = (value: any): string => {
  if (value === null || value === undefined) return 'Not set'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

const getValueClass = (): string => {
  if (props.value === 'Not set' || props.value === null || props.value === undefined) {
    return 'text-gray-500 italic'
  }
  return 'text-gray-900'
}
</script>