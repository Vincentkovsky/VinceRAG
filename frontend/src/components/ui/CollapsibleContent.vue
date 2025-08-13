<template>
  <div
    v-if="isOpen"
    :class="cn('overflow-hidden transition-all duration-200', $attrs.class as string)"
  >
    <slot />
  </div>
</template>

<script setup lang="ts">
import { inject, computed } from 'vue'
import { cn } from '@/lib/utils'

const collapsibleContext = inject('collapsibleContext') as any

const isOpen = computed(() => collapsibleContext?.isOpen.value)
</script>