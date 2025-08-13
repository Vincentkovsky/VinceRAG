<template>
  <Teleport to="body">
    <div
      v-if="isOpen"
      class="fixed inset-0 z-50 flex items-center justify-center"
      @click="onBackdropClick"
    >
      <!-- Backdrop -->
      <div class="fixed inset-0 bg-background/80 backdrop-blur-sm" />
      
      <!-- Dialog -->
      <div
        :class="cn(
          'relative z-50 grid w-full max-w-lg gap-4 border bg-background p-6 shadow-lg duration-200 sm:rounded-lg',
          dialogClass
        )"
        @click.stop
      >
        <!-- Close button -->
        <button
          v-if="showClose"
          @click="close"
          class="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
        >
          <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
          <span class="sr-only">Close</span>
        </button>
        
        <!-- Header -->
        <div v-if="$slots.header || title" class="flex flex-col space-y-1.5 text-center sm:text-left">
          <slot name="header">
            <h2 v-if="title" class="text-lg font-semibold leading-none tracking-tight">
              {{ title }}
            </h2>
            <p v-if="description" class="text-sm text-muted-foreground">
              {{ description }}
            </p>
          </slot>
        </div>
        
        <!-- Content -->
        <div class="flex-1">
          <slot />
        </div>
        
        <!-- Footer -->
        <div v-if="$slots.footer" class="flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2">
          <slot name="footer" :close="close" />
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { cn } from '@/lib/utils'

interface Props {
  open?: boolean
  title?: string
  description?: string
  showClose?: boolean
  closeOnBackdrop?: boolean
  class?: string
}

const props = withDefaults(defineProps<Props>(), {
  showClose: true,
  closeOnBackdrop: true
})

const dialogClass = props.class

const emit = defineEmits<{
  'update:open': [value: boolean]
  'close': []
}>()

const isOpen = ref(props.open || false)

watch(() => props.open, (newValue) => {
  isOpen.value = newValue || false
})

watch(isOpen, (newValue) => {
  emit('update:open', newValue)
  if (!newValue) {
    emit('close')
  }
})

function close() {
  isOpen.value = false
}

function onBackdropClick() {
  if (props.closeOnBackdrop) {
    close()
  }
}

function onEscapeKey(event: KeyboardEvent) {
  if (event.key === 'Escape' && isOpen.value) {
    close()
  }
}

onMounted(() => {
  document.addEventListener('keydown', onEscapeKey)
})

onUnmounted(() => {
  document.removeEventListener('keydown', onEscapeKey)
})

defineExpose({
  close,
  open: () => { isOpen.value = true }
})
</script>