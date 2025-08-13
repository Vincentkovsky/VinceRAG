<template>
  <div
    :class="cn(avatarVariants({ size }), $attrs.class as string)"
  >
    <img
      v-if="src"
      :src="src"
      :alt="alt"
      class="aspect-square h-full w-full object-cover"
      @error="onImageError"
    />
    <div
      v-else-if="fallback"
      class="flex h-full w-full items-center justify-center bg-muted text-muted-foreground font-medium"
    >
      {{ fallback }}
    </div>
    <div
      v-else
      class="flex h-full w-full items-center justify-center bg-muted text-muted-foreground"
    >
      <slot>
        <svg
          class="h-1/2 w-1/2"
          fill="currentColor"
          viewBox="0 0 24 24"
        >
          <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
        </svg>
      </slot>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { cva } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const avatarVariants = cva(
  'relative flex shrink-0 overflow-hidden rounded-full',
  {
    variants: {
      size: {
        sm: 'h-8 w-8',
        default: 'h-10 w-10',
        lg: 'h-12 w-12',
        xl: 'h-16 w-16',
      },
    },
    defaultVariants: {
      size: 'default',
    },
  }
)

interface Props {
  src?: string
  alt?: string
  fallback?: string
  size?: 'sm' | 'default' | 'lg' | 'xl'
}

defineProps<Props>()
const imageError = ref(false)

function onImageError() {
  imageError.value = true
}
</script>