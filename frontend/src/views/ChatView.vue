<template>
  <div class="h-full flex flex-col lg:flex-row gap-6">
    <!-- Main Chat Area -->
    <div class="flex-1 flex flex-col min-h-0">
      <!-- Header -->
      <div class="flex items-center justify-between mb-4">
        <div class="flex items-center gap-4">
          <h1 class="text-2xl font-bold">Chat</h1>
          <Badge v-if="chatStore.currentSession" variant="secondary" class="text-xs">
            Session {{ chatStore.currentSession.id }}
          </Badge>
        </div>
        
        <div class="flex items-center gap-2">
          <!-- Search Toggle -->
          <Button
            variant="ghost"
            size="sm"
            @click="showSearch = !showSearch"
            :class="{ 'bg-muted': showSearch }"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </Button>
          
          <!-- Sessions Toggle -->
          <Button
            variant="ghost"
            size="sm"
            @click="showSessions = !showSessions"
            :class="{ 'bg-muted': showSessions }"
            class="hidden lg:flex"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
          </Button>
          
          <!-- New Chat -->
          <Button
            variant="outline"
            size="sm"
            @click="startNewChat"
            :disabled="!chatStore.hasMessages"
          >
            <svg class="h-4 w-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
            New Chat
          </Button>
        </div>
      </div>

      <!-- Search Panel -->
      <div v-if="showSearch" class="mb-4">
        <Card class="p-4">
          <MessageSearch @message-selected="scrollToMessage" />
        </Card>
      </div>

      <!-- Chat Container -->
      <Card class="flex-1 flex flex-col min-h-0">
        <!-- Messages Area -->
        <ScrollArea
          ref="messagesScrollArea"
          class="flex-1 p-4"
          :scrollbar-class="'scrollbar-thin scrollbar-thumb-border scrollbar-track-transparent'"
        >
          <!-- Welcome Message -->
          <div v-if="!chatStore.hasMessages" class="flex items-center justify-center h-full text-muted-foreground">
            <div class="text-center space-y-4 max-w-md">
              <div class="text-6xl">💬</div>
              <div>
                <h2 class="text-xl font-semibold mb-2">Welcome to RAG Chat</h2>
                <p class="text-sm">Ask questions about your uploaded documents and web content.</p>
              </div>
              
              <div v-if="documentsStore.documentsByStatus.completed.length === 0" class="space-y-2">
                <Alert>
                  <template #icon>
                    <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </template>
                  <div class="text-sm">
                    <p class="font-medium">No documents uploaded</p>
                    <p>Upload documents first to get better answers to your questions.</p>
                  </div>
                </Alert>
                
                <Button
                  variant="outline"
                  size="sm"
                  @click="$router.push('/documents')"
                  class="w-full"
                >
                  Go to Documents
                </Button>
              </div>
            </div>
          </div>
          
          <!-- Messages -->
          <div v-else class="space-y-6">
            <ChatMessage
              v-for="message in chatStore.messages"
              :key="message.id"
              :message="message"
              @copy-message="onCopyMessage"
              @regenerate="onRegenerateMessage"
              @view-chunk="onViewChunk"
            />
            
            <!-- Streaming Message -->
            <ChatMessage
              v-if="chatStore.isStreaming"
              :message="{
                id: 0,
                type: 'assistant',
                content: chatStore.streamingMessage,
                timestamp: new Date()
              }"
              :is-streaming="true"
            />
          </div>
        </ScrollArea>

        <!-- Input Area -->
        <div class="border-t p-4">
          <ChatInput />
        </div>
      </Card>
    </div>

    <!-- Sidebar -->
    <div
      v-if="showSessions"
      class="w-full lg:w-80 flex-shrink-0"
    >
      <Card class="h-full p-4">
        <Tabs
          :tabs="sidebarTabs"
          v-model="activeSidebarTab"
          class="h-full flex flex-col"
        >
          <template #default="{ activeTab }">
            <div class="flex-1 mt-4 overflow-hidden">
              <ChatSessions
                v-if="activeTab === 'sessions'"
                ref="chatSessionsRef"
              />
              
              <div v-else-if="activeTab === 'settings'" class="space-y-4">
                <h3 class="font-semibold">Chat Settings</h3>
                
                <div class="space-y-3">
                  <div class="flex items-center justify-between">
                    <label class="text-sm font-medium">Streaming responses</label>
                    <input
                      type="checkbox"
                      v-model="streamingEnabled"
                      class="rounded border-input"
                    />
                  </div>
                  
                  <div class="flex items-center justify-between">
                    <label class="text-sm font-medium">Show timestamps</label>
                    <input
                      type="checkbox"
                      v-model="showTimestamps"
                      class="rounded border-input"
                    />
                  </div>
                  
                  <Separator />
                  
                  <Button
                    variant="destructive"
                    size="sm"
                    @click="clearAllHistory"
                    class="w-full"
                  >
                    Clear All History
                  </Button>
                </div>
              </div>
            </div>
          </template>
        </Tabs>
      </Card>
    </div>

    <!-- Mobile Sessions Dialog -->
    <Dialog
      v-model:open="showMobileSessions"
      title="Chat Sessions"
      class="lg:hidden"
    >
      <ChatSessions />
    </Dialog>

    <!-- Chunk Viewer Dialog -->
    <Dialog
      v-model:open="showChunkViewer"
      :title="selectedChunk?.documentName"
      class="max-w-2xl"
    >
      <div v-if="selectedChunk" class="space-y-4">
        <div class="flex items-center gap-2">
          <Badge variant="outline">
            Chunk {{ selectedChunk.chunkIndex + 1 }}
          </Badge>
          <Badge variant="secondary">
            {{ Math.round(selectedChunk.similarity * 100) }}% match
          </Badge>
        </div>
        
        <div class="prose prose-sm max-w-none dark:prose-invert">
          <div v-if="selectedChunk.highlighted" v-html="selectedChunk.highlighted" />
          <p v-else>{{ selectedChunk.chunk }}</p>
        </div>
        
        <div class="flex items-center justify-between text-sm text-muted-foreground">
          <span>{{ selectedChunk.tokenCount }} tokens</span>
          <span v-if="selectedChunk.url">
            <a :href="selectedChunk.url" target="_blank" class="hover:text-foreground underline">
              View original
            </a>
          </span>
        </div>
      </div>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, watch } from 'vue'
import { useChatStore } from '@/stores/chat'
import { useDocumentsStore } from '@/stores/documents'
import { useAppStore } from '@/stores/app'
import type { ChatMessage as ChatMessageType, DocumentSource } from '@/types'

// Components
import Card from '@/components/ui/Card.vue'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import Alert from '@/components/ui/Alert.vue'
import Dialog from '@/components/ui/Dialog.vue'
import Tabs from '@/components/ui/Tabs.vue'
import Separator from '@/components/ui/Separator.vue'
import ScrollArea from '@/components/ui/ScrollArea.vue'

import ChatInput from '@/components/chat/ChatInput.vue'
import ChatMessage from '@/components/chat/ChatMessage.vue'
import ChatSessions from '@/components/chat/ChatSessions.vue'
import MessageSearch from '@/components/chat/MessageSearch.vue'

const chatStore = useChatStore()
const documentsStore = useDocumentsStore()
const appStore = useAppStore()

// Refs
const messagesScrollArea = ref<InstanceType<typeof ScrollArea>>()
const chatSessionsRef = ref<InstanceType<typeof ChatSessions>>()

// State
const showSearch = ref(false)
const showSessions = ref(true)
const showMobileSessions = ref(false)
const showChunkViewer = ref(false)
const selectedChunk = ref<DocumentSource | null>(null)
const activeSidebarTab = ref('sessions')
const streamingEnabled = ref(true)
const showTimestamps = ref(false)

const sidebarTabs = [
  { value: 'sessions', label: 'Sessions' },
  { value: 'settings', label: 'Settings' }
]

// Methods
async function startNewChat() {
  chatStore.startNewSession()
  appStore.addNotification({
    type: 'success',
    title: 'New Chat',
    message: 'Started a new chat session'
  })
  
  // Scroll to bottom
  await nextTick()
  scrollToBottom()
}

function scrollToBottom() {
  messagesScrollArea.value?.scrollToBottom()
}

function scrollToMessage(_message: ChatMessageType) {
  // This would need to be implemented to scroll to a specific message
  // For now, just close search and scroll to bottom
  showSearch.value = false
  scrollToBottom()
}

function onCopyMessage(_message: ChatMessageType) {
  // Already handled in ChatMessage component
}

async function onRegenerateMessage(message: ChatMessageType) {
  // Find the user message that prompted this response
  const messageIndex = chatStore.messages.findIndex(m => m.id === message.id)
  if (messageIndex > 0) {
    const userMessage = chatStore.messages[messageIndex - 1]
    if (userMessage.type === 'user') {
      try {
        // Remove the assistant message
        chatStore.messages.splice(messageIndex, 1)
        
        // Resend the user message
        if (streamingEnabled.value) {
          await chatStore.sendStreamingMessage(userMessage.content)
        } else {
          await chatStore.sendMessage(userMessage.content)
        }
        
        scrollToBottom()
      } catch (error) {
        appStore.addNotification({
          type: 'error',
          title: 'Regeneration Failed',
          message: 'Failed to regenerate response'
        })
      }
    }
  }
}

function onViewChunk(source: DocumentSource) {
  selectedChunk.value = source
  showChunkViewer.value = true
}

async function clearAllHistory() {
  if (!confirm('Are you sure you want to clear all chat history? This cannot be undone.')) {
    return
  }
  
  try {
    await chatStore.clearChatHistory()
    chatSessionsRef.value?.loadSessions()
    
    appStore.addNotification({
      type: 'success',
      title: 'History Cleared',
      message: 'All chat history has been cleared'
    })
  } catch (error) {
    appStore.addNotification({
      type: 'error',
      title: 'Clear Failed',
      message: 'Failed to clear chat history'
    })
  }
}

// Watch for new messages and scroll to bottom
watch(() => chatStore.messages.length, () => {
  nextTick(() => {
    scrollToBottom()
  })
})

// Watch for streaming messages and scroll to bottom
watch(() => chatStore.streamingMessage, () => {
  nextTick(() => {
    scrollToBottom()
  })
})

onMounted(async () => {
  // Load chat history and documents
  await Promise.all([
    chatStore.loadChatHistory(),
    documentsStore.fetchDocuments()
  ])
  
  // Scroll to bottom after loading
  await nextTick()
  scrollToBottom()
})
</script>

<style scoped>
/* Mobile-first responsive design */
@media (max-width: 768px) {
  .lg\:flex-row {
    flex-direction: column;
  }
  
  .lg\:w-80 {
    width: 100%;
  }
}

/* Ensure proper scrolling on mobile */
@media (max-height: 600px) {
  .min-h-0 {
    min-height: 400px;
  }
}

/* Custom scrollbar for webkit browsers */
:deep(.scrollbar-thin) {
  scrollbar-width: thin;
  scrollbar-color: hsl(var(--border)) transparent;
}

:deep(.scrollbar-thin::-webkit-scrollbar) {
  width: 6px;
}

:deep(.scrollbar-thin::-webkit-scrollbar-track) {
  background: transparent;
}

:deep(.scrollbar-thin::-webkit-scrollbar-thumb) {
  background-color: hsl(var(--border));
  border-radius: 3px;
}

:deep(.scrollbar-thin::-webkit-scrollbar-thumb:hover) {
  background-color: hsl(var(--border) / 0.8);
}
</style>