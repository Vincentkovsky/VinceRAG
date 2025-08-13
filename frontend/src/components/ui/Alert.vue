<template>
  <div
    :class="cn(alertVariants({ variant }), $attrs.class as string)"
    role="alert"
  >
    <div v-if="$slots.icon || showIcon" class="flex-shrink-0">
      <slot name="icon">
        <svg
          v-if="variant === 'destructive'"
          class="h-4 w-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
        </svg>
        <svg
          v-else-if="variant === 'default'"
          class="h-4 w-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </slot>
    </div>
    
    <div class="flex-1">
      <h5 v-if="title" class="mb-1 font-medium leading-none tracking-tight">
        {{ title }}
      </h5>
      <div class="text-sm [&_p]:leading-relaxed">
        <slot>
          {{ description }}
        </slot>
      </div>
    </div>
    
    <button
      v-if="dismissible"
      @click="$emit('dismiss')"
      class="flex-shrink-0 ml-2 opacity-70 hover:opacity-100 transition-opacity"
    >
      <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
      </svg>
    </button>
  </div>
</template>

<script setup lang="ts">
import { cva } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const alertVariants = cva(
  'relative w-full rounded-lg border p-4 [&>svg~*]:pl-7 [&>svg+div]:translate-y-[-3px] [&>svg]:absolute [&>svg]:left-4 [&>svg]:top-4 [&>svg]:text-foreground',
  {
    variants: {
      variant: {
        default: 'bg-background text-foreground',
        destructive: 'border-destructive/50 text-destructive dark:border-destructive [&>svg]:text-destructive',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
)

interface Props {
  variant?: 'default' | 'destructive'
  title?: string
  description?: string
  dismissible?: boolean
  showIcon?: boolean
}

withDefaults(defineProps<Props>(), {
  showIcon: true
})

defineEmits<{
  dismiss: []
}>()
</script>