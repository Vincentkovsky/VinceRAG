<template>
  <button
    @click="handleClick"
    :class="cn(
      'inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50',
      isActive
        ? 'bg-background text-foreground shadow-sm'
        : 'hover:bg-background/50',
      $attrs.class as string
    )"
    :disabled="disabled"
  >
    <slot />
  </button>
</template>

<script setup lang="ts">
import { inject, computed } from 'vue'
import { cn } from '@/lib/utils'

interface Props {
  value: string
  disabled?: boolean
}

const props = defineProps<Props>()

const tabsContext = inject('tabsContext') as any

const isActive = computed(() => tabsContext?.activeTab.value === props.value)

const handleClick = () => {
  if (!props.disabled) {
    tabsContext?.setActiveTab(props.value)
  }
}
</script>