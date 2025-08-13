<template>
  <div
    v-if="isActive"
    :class="cn(
      'mt-2 ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
      $attrs.class as string
    )"
  >
    <slot />
  </div>
</template>

<script setup lang="ts">
import { inject, computed } from 'vue'
import { cn } from '@/lib/utils'

interface Props {
  value: string
}

const props = defineProps<Props>()

const tabsContext = inject('tabsContext') as any

const isActive = computed(() => tabsContext?.activeTab.value === props.value)
</script>