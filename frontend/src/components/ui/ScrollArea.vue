<template>
  <div
    :class="cn('relative overflow-hidden', $attrs.class as string)"
    ref="scrollAreaRef"
  >
    <div
      :class="cn('h-full w-full rounded-[inherit]', scrollbarClass)"
      :style="{ overflow: 'auto' }"
      @scroll="onScroll"
    >
      <slot />
    </div>
    
    <!-- Custom scrollbar track (optional) -->
    <div
      v-if="showScrollbar && isScrollable"
      class="absolute right-0 top-0 h-full w-2 bg-border/20 rounded-full"
    >
      <div
        class="bg-border/60 rounded-full transition-colors hover:bg-border/80"
        :style="{
          height: `${scrollbarHeight}%`,
          transform: `translateY(${scrollbarPosition}px)`
        }"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { cn } from '@/lib/utils'

interface Props {
  showScrollbar?: boolean
  scrollbarClass?: string
}

withDefaults(defineProps<Props>(), {
  showScrollbar: false,
  scrollbarClass: 'scrollbar-thin scrollbar-thumb-border scrollbar-track-transparent'
})

const scrollAreaRef = ref<HTMLElement>()
const scrollTop = ref(0)
const scrollHeight = ref(0)
const clientHeight = ref(0)

const isScrollable = computed(() => scrollHeight.value > clientHeight.value)
const scrollbarHeight = computed(() => (clientHeight.value / scrollHeight.value) * 100)
const scrollbarPosition = computed(() => (scrollTop.value / (scrollHeight.value - clientHeight.value)) * (clientHeight.value - (clientHeight.value * scrollbarHeight.value / 100)))

function onScroll(event: Event) {
  const target = event.target as HTMLElement
  scrollTop.value = target.scrollTop
  scrollHeight.value = target.scrollHeight
  clientHeight.value = target.clientHeight
}

function updateScrollInfo() {
  if (scrollAreaRef.value) {
    const scrollContainer = scrollAreaRef.value.querySelector('[style*="overflow"]') as HTMLElement
    if (scrollContainer) {
      scrollHeight.value = scrollContainer.scrollHeight
      clientHeight.value = scrollContainer.clientHeight
      scrollTop.value = scrollContainer.scrollTop
    }
  }
}

onMounted(() => {
  updateScrollInfo()
  window.addEventListener('resize', updateScrollInfo)
})

onUnmounted(() => {
  window.removeEventListener('resize', updateScrollInfo)
})

defineExpose({
  scrollToBottom: () => {
    const scrollContainer = scrollAreaRef.value?.querySelector('[style*="overflow"]') as HTMLElement
    if (scrollContainer) {
      scrollContainer.scrollTop = scrollContainer.scrollHeight
    }
  },
  scrollToTop: () => {
    const scrollContainer = scrollAreaRef.value?.querySelector('[style*="overflow"]') as HTMLElement
    if (scrollContainer) {
      scrollContainer.scrollTop = 0
    }
  }
})
</script>