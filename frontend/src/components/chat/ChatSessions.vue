<template>
  <div class="space-y-4">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <h3 class="text-lg font-semibold">Chat Sessions</h3>
      <Button
        @click="createNewSession"
        size="sm"
        :disabled="isLoading"
      >
        New Chat
      </Button>
    </div>
    
    <!-- Sessions List -->
    <div class="space-y-2 max-h-96 overflow-y-auto">
      <div
        v-for="session in sessions"
        :key="session.id"
        :class="cn(
          'flex items-center justify-between p-3 rounded-lg border cursor-pointer transition-colors',
          currentSessionId === session.id
            ? 'bg-primary/10 border-primary'
            : 'hover:bg-muted/50'
        )"
        @click="selectSession(session)"
      >
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2">
            <span class="font-medium text-sm truncate">
              {{ getSessionTitle(session) }}
            </span>
            <Badge
              v-if="currentSessionId === session.id"
              variant="secondary"
              class="text-xs"
            >
              Active
            </Badge>
          </div>
          
          <div class="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
            <span>{{ formatDate(session.createdAt) }}</span>
            <span v-if="session.messageCount">
              • {{ session.messageCount }} message{{ session.messageCount > 1 ? 's' : '' }}
            </span>
          </div>
        </div>
        
        <div class="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            @click.stop="exportSession(session)"
            class="h-8 w-8 p-0"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </Button>
          
          <Button
            variant="ghost"
            size="sm"
            @click.stop="deleteSession(session)"
            class="h-8 w-8 p-0 text-destructive hover:text-destructive"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </Button>
        </div>
      </div>
      
      <!-- Empty State -->
      <div
        v-if="sessions.length === 0 && !isLoading"
        class="text-center py-8 text-muted-foreground"
      >
        <p>No chat sessions yet</p>
        <p class="text-sm">Start a conversation to create your first session</p>
      </div>
      
      <!-- Loading State -->
      <div v-if="isLoading" class="space-y-2">
        <div v-for="i in 3" :key="i" class="flex items-center space-x-3 p-3">
          <Skeleton class="h-10 w-10 rounded-full" />
          <div class="space-y-2 flex-1">
            <Skeleton class="h-4 w-3/4" />
            <Skeleton class="h-3 w-1/2" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import type { ChatSession } from '@/types'
import { formatDate, cn } from '@/lib/utils'
import { chatApi } from '@/api/chat'
import { useChatStore } from '@/stores/chat'
import { useAppStore } from '@/stores/app'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import Skeleton from '@/components/ui/Skeleton.vue'

interface ExtendedChatSession extends ChatSession {
  messageCount?: number
  lastMessage?: string
  title?: string
}

const chatStore = useChatStore()
const appStore = useAppStore()

const sessions = ref<ExtendedChatSession[]>([])
const isLoading = ref(false)

const currentSessionId = computed(() => chatStore.currentSession?.id)

async function loadSessions() {
  isLoading.value = true
  try {
    const response = await chatApi.getChatSessions()
    sessions.value = response
  } catch (error) {
    appStore.addNotification({
      type: 'error',
      title: 'Load Failed',
      message: 'Failed to load chat sessions'
    })
  } finally {
    isLoading.value = false
  }
}

async function createNewSession() {
  try {
    chatStore.startNewSession()
    appStore.addNotification({
      type: 'success',
      title: 'New Session',
      message: 'Started a new chat session'
    })
  } catch (error) {
    appStore.addNotification({
      type: 'error',
      title: 'Session Failed',
      message: 'Failed to create new session'
    })
  }
}

async function selectSession(session: ExtendedChatSession) {
  try {
    // Load the session's chat history
    const response = await chatApi.getChatHistory(session.id)
    chatStore.messages = response.messages
    chatStore.currentSession = session
    
    appStore.addNotification({
      type: 'success',
      title: 'Session Loaded',
      message: `Loaded chat session from ${formatDate(session.createdAt)}`
    })
  } catch (error) {
    appStore.addNotification({
      type: 'error',
      title: 'Load Failed',
      message: 'Failed to load chat session'
    })
  }
}

async function deleteSession(session: ExtendedChatSession) {
  if (!confirm('Are you sure you want to delete this chat session?')) {
    return
  }
  
  try {
    await chatApi.deleteSession(session.id)
    sessions.value = sessions.value.filter(s => s.id !== session.id)
    
    // If this was the current session, start a new one
    if (currentSessionId.value === session.id) {
      chatStore.startNewSession()
    }
    
    appStore.addNotification({
      type: 'success',
      title: 'Session Deleted',
      message: 'Chat session deleted successfully'
    })
  } catch (error) {
    appStore.addNotification({
      type: 'error',
      title: 'Delete Failed',
      message: 'Failed to delete chat session'
    })
  }
}

async function exportSession(session: ExtendedChatSession) {
  try {
    // Load session messages if not current session
    let messages = chatStore.messages
    if (currentSessionId.value !== session.id) {
      const response = await chatApi.getChatHistory(session.id)
      messages = response.messages
    }
    
    // Create export content
    const exportContent = messages.map(msg => {
      const timestamp = new Date(msg.timestamp).toLocaleString()
      const role = msg.type === 'user' ? 'User' : 'Assistant'
      let content = `[${timestamp}] ${role}: ${msg.content}`
      
      if (msg.sources && msg.sources.length > 0) {
        content += '\n\nSources:'
        msg.sources.forEach((source, index) => {
          content += `\n${index + 1}. ${source.documentName} (${Math.round(source.similarity * 100)}% match)`
        })
      }
      
      return content
    }).join('\n\n---\n\n')
    
    // Download as text file
    const blob = new Blob([exportContent], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `chat-session-${session.id}-${new Date().toISOString().split('T')[0]}.txt`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    
    appStore.addNotification({
      type: 'success',
      title: 'Export Complete',
      message: 'Chat session exported successfully'
    })
  } catch (error) {
    appStore.addNotification({
      type: 'error',
      title: 'Export Failed',
      message: 'Failed to export chat session'
    })
  }
}

function getSessionTitle(session: ExtendedChatSession): string {
  if (session.title) return session.title
  if (session.lastMessage) return session.lastMessage.substring(0, 50) + '...'
  return `Chat ${session.id}`
}

onMounted(() => {
  loadSessions()
})

defineExpose({
  loadSessions,
  createNewSession
})
</script>