<template>
  <div :class="cn('w-full', $attrs.class as string)">
    <!-- Tab List -->
    <div
      :class="cn(
        'inline-flex h-10 items-center justify-center rounded-md bg-muted p-1 text-muted-foreground',
        tabsListClass
      )"
    >
      <button
        v-for="tab in tabs"
        :key="tab.value"
        @click="setActiveTab(tab.value)"
        :class="cn(
          'inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50',
          activeTab === tab.value
            ? 'bg-background text-foreground shadow-sm'
            : 'hover:bg-background/50',
          tabTriggerClass
        )"
        :disabled="tab.disabled"
      >
        {{ tab.label }}
      </button>
    </div>
    
    <!-- Tab Content -->
    <div class="mt-2">
      <slot :activeTab="activeTab" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { cn } from '@/lib/utils'

interface Tab {
  value: string
  label: string
  disabled?: boolean
}

interface Props {
  tabs: Tab[]
  defaultValue?: string
  modelValue?: string
  tabsListClass?: string
  tabTriggerClass?: string
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'update:modelValue': [value: string]
  'change': [value: string]
}>()

const activeTab = ref(props.modelValue || props.defaultValue || props.tabs[0]?.value || '')

watch(() => props.modelValue, (newValue) => {
  if (newValue && newValue !== activeTab.value) {
    activeTab.value = newValue
  }
})

function setActiveTab(value: string) {
  activeTab.value = value
  emit('update:modelValue', value)
  emit('change', value)
}

defineExpose({
  setActiveTab,
  activeTab: () => activeTab.value
})
</script>