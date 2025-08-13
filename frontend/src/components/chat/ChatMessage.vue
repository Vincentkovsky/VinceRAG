<template>
  <div
    class="flex gap-3 group"
    :class="message.type === 'user' ? 'justify-end' : 'justify-start'"
  >
    <!-- Avatar -->
    <Avatar
      v-if="message.type === 'assistant'"
      :fallback="'AI'"
      size="sm"
      class="mt-1"
    />
    
    <!-- Message Content -->
    <div
      class="max-w-[80%] space-y-2"
      :class="message.type === 'user' ? 'order-first' : ''"
    >
      <!-- Message Bubble -->
      <div
        :class="cn(
          'rounded-lg px-4 py-3 text-sm',
          message.type === 'user'
            ? 'bg-primary text-primary-foreground ml-auto'
            : 'bg-muted text-foreground'
        )"
      >
        <!-- Message Content -->
        <div
          v-if="message.content"
          class="prose prose-sm max-w-none dark:prose-invert"
          :class="message.type === 'user' ? 'prose-invert' : ''"
          v-html="formattedContent"
        />
        
        <!-- Streaming indicator -->
        <div v-if="isStreaming" class="flex items-center gap-2 mt-2 text-xs opacity-70">
          <div class="flex gap-1">
            <div class="w-1 h-1 bg-current rounded-full animate-bounce" />
            <div class="w-1 h-1 bg-current rounded-full animate-bounce" style="animation-delay: 0.1s" />
            <div class="w-1 h-1 bg-current rounded-full animate-bounce" style="animation-delay: 0.2s" />
          </div>
          <span>Thinking...</span>
        </div>
      </div>
      
      <!-- Sources -->
      <div v-if="message.sources && message.sources.length > 0" class="space-y-2">
        <Collapsible
          :default-open="false"
          trigger-class="text-xs text-muted-foreground hover:text-foreground"
        >
          <template #trigger>
            <div class="flex items-center gap-2">
              <span>{{ message.sources.length }} source{{ message.sources.length > 1 ? 's' : '' }}</span>
              <Badge variant="secondary" class="text-xs">
                {{ averageConfidence }}% confidence
              </Badge>
            </div>
          </template>
          
          <div class="space-y-2 mt-2">
            <div
              v-for="source in message.sources"
              :key="source.chunkId"
              class="border rounded-lg p-3 bg-background/50 hover:bg-background/80 transition-colors"
            >
              <!-- Source Header -->
              <div class="flex items-center justify-between mb-2">
                <div class="flex items-center gap-2">
                  <span class="text-xs font-medium">{{ source.documentName }}</span>
                  <Badge variant="outline" class="text-xs">
                    {{ Math.round(source.similarity * 100) }}% match
                  </Badge>
                </div>
                
                <div class="flex items-center gap-1 text-xs text-muted-foreground">
                  <span v-if="source.chunkIndex !== undefined">
                    Chunk {{ source.chunkIndex + 1 }}
                  </span>
                  <span v-if="source.contextInfo">
                    • {{ source.contextInfo.join(', ') }}
                  </span>
                </div>
              </div>
              
              <!-- Source Content -->
              <div class="text-xs text-muted-foreground">
                <div
                  v-if="source.highlighted"
                  v-html="source.highlighted"
                  class="line-clamp-3"
                />
                <div v-else class="line-clamp-3">
                  {{ source.chunk }}
                </div>
              </div>
              
              <!-- Source Actions -->
              <div class="flex items-center justify-between mt-2">
                <div class="flex items-center gap-2 text-xs text-muted-foreground">
                  <span v-if="source.url">
                    <a :href="source.url" target="_blank" class="hover:text-foreground underline">
                      View original
                    </a>
                  </span>
                  <span v-if="source.publishedDate">
                    {{ formatDate(source.publishedDate) }}
                  </span>
                </div>
                
                <Button
                  variant="ghost"
                  size="sm"
                  @click="viewFullChunk(source)"
                  class="text-xs h-6 px-2"
                >
                  View full
                </Button>
              </div>
            </div>
          </div>
        </Collapsible>
      </div>
      
      <!-- Message Actions -->
      <div class="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
        <Button
          variant="ghost"
          size="sm"
          @click="copyMessage"
          class="h-6 px-2 text-xs"
        >
          Copy
        </Button>
        
        <Button
          v-if="message.type === 'assistant'"
          variant="ghost"
          size="sm"
          @click="regenerateResponse"
          class="h-6 px-2 text-xs"
        >
          Regenerate
        </Button>
        
        <span class="text-xs text-muted-foreground ml-auto">
          {{ formatTime(message.timestamp) }}
        </span>
      </div>
    </div>
    
    <!-- User Avatar -->
    <Avatar
      v-if="message.type === 'user'"
      :fallback="'U'"
      size="sm"
      class="mt-1"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ChatMessage, DocumentSource } from '@/types'
import { formatDate, cn } from '@/lib/utils'
import Avatar from '@/components/ui/Avatar.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Collapsible from '@/components/ui/Collapsible.vue'
import { useAppStore } from '@/stores/app'

interface Props {
  message: ChatMessage
  isStreaming?: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'copy-message': [message: ChatMessage]
  'regenerate': [message: ChatMessage]
  'view-chunk': [source: DocumentSource]
}>()

const appStore = useAppStore()

const formattedContent = computed(() => {
  if (!props.message.content) return ''
  
  // Convert markdown-like formatting to HTML
  let content = props.message.content
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code class="bg-muted px-1 py-0.5 rounded text-xs">$1</code>')
    .replace(/\n/g, '<br>')
  
  return content
})

const averageConfidence = computed(() => {
  if (!props.message.sources || props.message.sources.length === 0) return 0
  
  const total = props.message.sources.reduce((sum, source) => sum + source.similarity, 0)
  return Math.round((total / props.message.sources.length) * 100)
})

function formatTime(date: Date) {
  return new Intl.DateTimeFormat('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  }).format(date)
}

async function copyMessage() {
  try {
    await navigator.clipboard.writeText(props.message.content)
    appStore.addNotification({
      type: 'success',
      title: 'Copied',
      message: 'Message copied to clipboard'
    })
  } catch (error) {
    appStore.addNotification({
      type: 'error',
      title: 'Copy Failed',
      message: 'Failed to copy message to clipboard'
    })
  }
  
  emit('copy-message', props.message)
}

function regenerateResponse() {
  emit('regenerate', props.message)
}

function viewFullChunk(source: DocumentSource) {
  emit('view-chunk', source)
}
</script>

<style scoped>
.line-clamp-3 {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.prose code {
  @apply bg-muted px-1 py-0.5 rounded text-xs;
}
</style>