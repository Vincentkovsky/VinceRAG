<template>
  <button
    @click="handleClick"
    :class="cn(
      'flex w-full items-center justify-between py-2 font-medium transition-all hover:underline',
      $attrs.class as string
    )"
  >
    <slot />
  </button>
</template>

<script setup lang="ts">
import { inject } from 'vue'
import { cn } from '@/lib/utils'

const collapsibleContext = inject('collapsibleContext') as any

const handleClick = () => {
  collapsibleContext?.toggle()
}
</script>