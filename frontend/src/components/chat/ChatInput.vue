<template>
  <div class="space-y-3">
    <!-- Document Filter -->
    <div v-if="documentsStore.documents.length > 0" class="flex items-center space-x-2">
      <span class="text-sm font-medium">Filter by documents:</span>
      <select
        v-model="selectedDocumentIds"
        multiple
        class="px-3 py-1 border border-input rounded-md bg-background text-sm max-w-xs"
      >
        <option value="">All documents</option>
        <option
          v-for="document in documentsStore.documentsByStatus.completed"
          :key="document.id"
          :value="document.id"
        >
          {{ getFileIcon(document.type) }} {{ document.name }}
        </option>
      </select>
    </div>

    <!-- Message Input -->
    <div class="flex space-x-2">
      <div class="flex-1">
        <textarea
          ref="messageInput"
          v-model="message"
          placeholder="Ask a question about your documents..."
          rows="1"
          class="w-full px-3 py-2 border border-input rounded-md bg-background text-sm resize-none min-h-[40px] max-h-32"
          :disabled="chatStore.isLoading || chatStore.isStreaming"
          @keydown="handleKeyDown"
          @input="adjustTextareaHeight"
        />
      </div>
      
      <Button
        @click="sendMessage"
        :disabled="!message.trim() || chatStore.isLoading || chatStore.isStreaming"
        class="px-4"
      >
        <span v-if="chatStore.isLoading || chatStore.isStreaming">
          Sending...
        </span>
        <span v-else>
          Send
        </span>
      </Button>
    </div>

    <!-- Quick Actions -->
    <div class="flex flex-wrap gap-2">
      <Button
        v-for="quickAction in quickActions"
        :key="quickAction.text"
        variant="outline"
        size="sm"
        @click="useQuickAction(quickAction.text)"
        :disabled="chatStore.isLoading || chatStore.isStreaming"
      >
        {{ quickAction.text }}
      </Button>
    </div>

    <!-- Typing Indicator -->
    <div v-if="chatStore.isStreaming" class="text-sm text-muted-foreground">
      <div class="flex items-center space-x-2">
        <div class="flex space-x-1">
          <div class="w-2 h-2 bg-primary rounded-full animate-bounce"></div>
          <div class="w-2 h-2 bg-primary rounded-full animate-bounce" style="animation-delay: 0.1s"></div>
          <div class="w-2 h-2 bg-primary rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
        </div>
        <span>AI is thinking...</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
import { useChatStore } from '@/stores/chat'
import { useDocumentsStore } from '@/stores/documents'
import { useAppStore } from '@/stores/app'
import { getFileIcon } from '@/lib/utils'
import Button from '@/components/ui/Button.vue'

const chatStore = useChatStore()
const documentsStore = useDocumentsStore()
const appStore = useAppStore()

const message = ref('')
const messageInput = ref<HTMLTextAreaElement>()
const selectedDocumentIds = ref<number[]>([])

const quickActions = [
  { text: 'Summarize the main points' },
  { text: 'What are the key findings?' },
  { text: 'Explain this in simple terms' },
  { text: 'What are the implications?' },
  { text: 'Compare different approaches' },
]

async function sendMessage() {
  if (!message.value.trim()) return
  
  try {
    // Use streaming if available, otherwise regular message
    if (appStore.config?.features?.streaming) {
      await chatStore.sendStreamingMessage(message.value)
    } else {
      await chatStore.sendMessage(message.value)
    }
    
    // Clear input
    message.value = ''
    adjustTextareaHeight()
    
    // Focus back to input
    nextTick(() => {
      messageInput.value?.focus()
    })
    
  } catch (error) {
    appStore.addNotification({
      type: 'error',
      title: 'Message Failed',
      message: 'Failed to send message. Please try again.'
    })
  }
}

function handleKeyDown(event: KeyboardEvent) {
  // Send on Ctrl/Cmd + Enter
  if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
    event.preventDefault()
    sendMessage()
  }
  
  // Prevent default Enter behavior in textarea
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    sendMessage()
  }
}

function adjustTextareaHeight() {
  if (!messageInput.value) return
  
  // Reset height to auto to get the correct scrollHeight
  messageInput.value.style.height = 'auto'
  
  // Set height based on scrollHeight, with min and max constraints
  const minHeight = 40 // min-h-[40px]
  const maxHeight = 128 // max-h-32 (32 * 4 = 128px)
  const scrollHeight = messageInput.value.scrollHeight
  
  const newHeight = Math.min(Math.max(scrollHeight, minHeight), maxHeight)
  messageInput.value.style.height = `${newHeight}px`
}

function useQuickAction(actionText: string) {
  message.value = actionText
  adjustTextareaHeight()
  messageInput.value?.focus()
}

onMounted(() => {
  // Focus input on mount
  messageInput.value?.focus()
})
</script>