<template>
  <div>
    <button
      @click="toggle"
      :class="cn(
        'flex w-full items-center justify-between py-2 font-medium transition-all hover:underline',
        triggerClass
      )"
      :aria-expanded="isOpen"
    >
      <slot name="trigger" :isOpen="isOpen">
        {{ title }}
      </slot>
      
      <svg
        class="h-4 w-4 shrink-0 transition-transform duration-200"
        :class="{ 'rotate-180': isOpen }"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
      </svg>
    </button>
    
    <div
      v-show="isOpen"
      :class="cn('overflow-hidden transition-all duration-200', contentClass)"
    >
      <div class="pb-4 pt-0">
        <slot :isOpen="isOpen" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { cn } from '@/lib/utils'

interface Props {
  title?: string
  defaultOpen?: boolean
  triggerClass?: string
  contentClass?: string
}

const props = withDefaults(defineProps<Props>(), {
  defaultOpen: false
})

const isOpen = ref(props.defaultOpen)

function toggle() {
  isOpen.value = !isOpen.value
}

defineExpose({
  toggle,
  open: () => { isOpen.value = true },
  close: () => { isOpen.value = false },
  isOpen: () => isOpen.value
})
</script>