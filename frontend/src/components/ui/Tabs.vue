<template>
  <div :class="cn('w-full', $attrs.class as string)">
    <slot />
  </div>
</template>

<script setup lang="ts">
import { provide, ref, watch } from 'vue'
import { cn } from '@/lib/utils'

interface Props {
  modelValue?: string
  defaultValue?: string
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const activeTab = ref(props.modelValue || props.defaultValue || '')

watch(() => props.modelValue, (newValue) => {
  if (newValue !== undefined) {
    activeTab.value = newValue
  }
})

const setActiveTab = (value: string) => {
  activeTab.value = value
  emit('update:modelValue', value)
}

provide('tabsContext', {
  activeTab,
  setActiveTab
})
</script>