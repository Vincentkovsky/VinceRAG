<template>
  <div class="space-y-3">
    <!-- Document Filter -->
    <div v-if="documentsStore.documents.length > 0" class="space-y-2">
      <div class="flex items-center justify-between">
        <span class="text-sm font-medium">Filter by documents:</span>
        <Button
          variant="ghost"
          size="sm"
          @click="clearDocumentFilter"
          v-if="selectedDocumentIds.length > 0"
          class="text-xs h-6 px-2"
        >
          Clear filter
        </Button>
      </div>
      
      <div class="flex flex-wrap gap-2 max-h-24 overflow-y-auto">
        <Button
          v-for="document in documentsStore.documentsByStatus.completed"
          :key="document.id"
          :variant="selectedDocumentIds.includes(document.id) ? 'default' : 'outline'"
          size="sm"
          @click="toggleDocumentFilter(document.id)"
          class="text-xs h-7"
        >
          {{ getFileIcon(document.type) }} {{ document.name }}
        </Button>
      </div>
      
      <div v-if="selectedDocumentIds.length > 0" class="text-xs text-muted-foreground">
        Searching in {{ selectedDocumentIds.length }} document{{ selectedDocumentIds.length > 1 ? 's' : '' }}
      </div>
    </div>

    <!-- Message Input -->
    <div class="relative">
      <div class="flex space-x-2">
        <div class="flex-1 relative">
          <textarea
            ref="messageInput"
            v-model="message"
            :placeholder="getPlaceholder()"
            rows="1"
            class="w-full px-3 py-2 pr-10 border border-input rounded-md bg-background text-sm resize-none min-h-[40px] max-h-32 focus:ring-2 focus:ring-ring focus:ring-offset-2"
            :disabled="chatStore.isLoading || chatStore.isStreaming"
            @keydown="handleKeyDown"
            @input="adjustTextareaHeight"
            @paste="handlePaste"
          />
          
          <!-- Character count -->
          <div
            v-if="message.length > 0"
            class="absolute bottom-1 right-2 text-xs text-muted-foreground"
            :class="{ 'text-destructive': message.length > maxMessageLength }"
          >
            {{ message.length }}{{ maxMessageLength ? `/${maxMessageLength}` : '' }}
          </div>
        </div>
        
        <Button
          @click="sendMessage"
          :disabled="!canSendMessage"
          class="px-4 self-end"
          :class="{ 'animate-pulse': chatStore.isStreaming }"
        >
          <svg
            v-if="chatStore.isLoading || chatStore.isStreaming"
            class="animate-spin h-4 w-4 mr-2"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
          </svg>
          
          <svg
            v-else
            class="h-4 w-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
          </svg>
          
          <span class="ml-2">
            {{ chatStore.isLoading || chatStore.isStreaming ? 'Sending...' : 'Send' }}
          </span>
        </Button>
      </div>
    </div>

    <!-- Quick Actions -->
    <div class="space-y-2">
      <div class="flex items-center justify-between">
        <span class="text-sm font-medium">Quick actions:</span>
        <Button
          variant="ghost"
          size="sm"
          @click="showAllQuickActions = !showAllQuickActions"
          class="text-xs h-6 px-2"
        >
          {{ showAllQuickActions ? 'Show less' : 'Show more' }}
        </Button>
      </div>
      
      <div class="flex flex-wrap gap-2">
        <Button
          v-for="quickAction in displayedQuickActions"
          :key="quickAction.text"
          variant="outline"
          size="sm"
          @click="useQuickAction(quickAction.text)"
          :disabled="chatStore.isLoading || chatStore.isStreaming"
          class="text-xs"
        >
          {{ quickAction.icon }} {{ quickAction.text }}
        </Button>
      </div>
    </div>

    <!-- Input Hints -->
    <div class="text-xs text-muted-foreground space-y-1">
      <div class="flex items-center gap-4">
        <span>💡 Press <kbd class="px-1 py-0.5 bg-muted rounded text-xs">Enter</kbd> to send</span>
        <span>Press <kbd class="px-1 py-0.5 bg-muted rounded text-xs">Shift+Enter</kbd> for new line</span>
      </div>
      <div v-if="documentsStore.documentsByStatus.completed.length === 0" class="text-amber-600 dark:text-amber-400">
        ⚠️ No documents uploaded yet. Upload documents to get better answers.
      </div>
    </div>

    <!-- Typing Indicator -->
    <div v-if="chatStore.isStreaming" class="flex items-center space-x-2 text-sm text-muted-foreground">
      <div class="flex space-x-1">
        <div class="w-2 h-2 bg-primary rounded-full animate-bounce"></div>
        <div class="w-2 h-2 bg-primary rounded-full animate-bounce" style="animation-delay: 0.1s"></div>
        <div class="w-2 h-2 bg-primary rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
      </div>
      <span>AI is thinking...</span>
      <Button
        variant="ghost"
        size="sm"
        @click="stopGeneration"
        class="text-xs h-6 px-2 ml-auto"
      >
        Stop
      </Button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted, computed } from 'vue'
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
const showAllQuickActions = ref(false)
const maxMessageLength = 4000

const quickActions = [
  { text: 'Summarize the main points', icon: '📝' },
  { text: 'What are the key findings?', icon: '🔍' },
  { text: 'Explain this in simple terms', icon: '💡' },
  { text: 'What are the implications?', icon: '🤔' },
  { text: 'Compare different approaches', icon: '⚖️' },
  { text: 'What are the pros and cons?', icon: '➕➖' },
  { text: 'Give me examples', icon: '📋' },
  { text: 'How does this relate to...?', icon: '🔗' },
  { text: 'What questions should I ask?', icon: '❓' },
  { text: 'Create an action plan', icon: '📋' },
]

const displayedQuickActions = computed(() => {
  return showAllQuickActions.value ? quickActions : quickActions.slice(0, 5)
})

const canSendMessage = computed(() => {
  return message.value.trim() && 
         !chatStore.isLoading && 
         !chatStore.isStreaming &&
         message.value.length <= maxMessageLength
})

async function sendMessage() {
  if (!canSendMessage.value) return
  
  try {
    const messageContent = message.value.trim()
    const documentIds = selectedDocumentIds.value.length > 0 ? selectedDocumentIds.value : undefined
    
    // Use streaming if available, otherwise regular message
    if (appStore.config?.features?.streaming) {
      await chatStore.sendStreamingMessage(messageContent, documentIds)
    } else {
      await chatStore.sendMessage(messageContent, documentIds)
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

function toggleDocumentFilter(documentId: number) {
  const index = selectedDocumentIds.value.indexOf(documentId)
  if (index > -1) {
    selectedDocumentIds.value.splice(index, 1)
  } else {
    selectedDocumentIds.value.push(documentId)
  }
}

function clearDocumentFilter() {
  selectedDocumentIds.value = []
}

function useQuickAction(actionText: string) {
  message.value = actionText
  adjustTextareaHeight()
  messageInput.value?.focus()
}

function getPlaceholder(): string {
  if (documentsStore.documentsByStatus.completed.length === 0) {
    return 'Upload documents first, then ask questions about them...'
  }
  
  if (selectedDocumentIds.value.length > 0) {
    const docNames = selectedDocumentIds.value
      .map(id => documentsStore.documents.find(d => d.id === id)?.name)
      .filter(Boolean)
      .slice(0, 2)
    
    return `Ask about ${docNames.join(', ')}${selectedDocumentIds.value.length > 2 ? ` and ${selectedDocumentIds.value.length - 2} more` : ''}...`
  }
  
  return 'Ask a question about your documents...'
}

function handlePaste(event: ClipboardEvent) {
  // Handle pasted content (could add file paste support here)
  const pastedText = event.clipboardData?.getData('text')
  if (pastedText && pastedText.length > maxMessageLength) {
    event.preventDefault()
    appStore.addNotification({
      type: 'warning',
      title: 'Text Too Long',
      message: `Pasted text is too long. Maximum ${maxMessageLength} characters allowed.`
    })
  }
}

function stopGeneration() {
  // This would need to be implemented in the chat store
  chatStore.stopStreaming?.()
}

onMounted(() => {
  // Focus input on mount
  messageInput.value?.focus()
})
</script>