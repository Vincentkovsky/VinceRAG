import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { ChatMessage, ChatSession } from '@/types'
import { chatApi } from '@/api/chat'

export const useChatStore = defineStore('chat', () => {
  // State
  const messages = ref<ChatMessage[]>([])
  const currentSession = ref<ChatSession | null>(null)
  const sessions = ref<ChatSession[]>([])
  const isLoading = ref(false)
  const isStreaming = ref(false)
  const streamingMessage = ref('')
  
  // Getters
  const lastMessage = computed(() => 
    messages.value[messages.value.length - 1]
  )
  
  const hasMessages = computed(() => messages.value.length > 0)
  
  // Actions
  async function sendMessage(content: string, documentIds?: number[]) {
    const userMessage: ChatMessage = {
      id: Date.now(), // Temporary ID
      type: 'user',
      content,
      timestamp: new Date()
    }
    
    messages.value.push(userMessage)
    isLoading.value = true
    
    try {
      const response = await chatApi.sendMessage(content, currentSession.value?.id, documentIds)
      
      // Update session if new
      if (response.sessionId && !currentSession.value) {
        currentSession.value = { id: response.sessionId, createdAt: new Date() }
      }
      
      const assistantMessage: ChatMessage = {
        id: response.messageId,
        type: 'assistant',
        content: response.answer,
        sources: response.sources,
        timestamp: new Date()
      }
      
      messages.value.push(assistantMessage)
    } catch (error) {
      console.error('Failed to send message:', error)
      throw error
    } finally {
      isLoading.value = false
    }
  }
  
  const streamController = ref<AbortController | null>(null)

  async function sendStreamingMessage(content: string, documentIds?: number[]) {
    const userMessage: ChatMessage = {
      id: Date.now(),
      type: 'user',
      content,
      timestamp: new Date()
    }
    
    messages.value.push(userMessage)
    isStreaming.value = true
    streamingMessage.value = ''
    
    // Create abort controller for stopping generation
    streamController.value = new AbortController()
    
    try {
      const stream = await chatApi.sendStreamingMessage(
        content, 
        currentSession.value?.id, 
        documentIds,
        streamController.value.signal
      )
      const reader = stream.getReader()
      
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        
        streamingMessage.value += value
      }
      
      const assistantMessage: ChatMessage = {
        id: Date.now(),
        type: 'assistant',
        content: streamingMessage.value,
        timestamp: new Date()
      }
      
      messages.value.push(assistantMessage)
    } catch (error) {
      if ((error as Error).name === 'AbortError') {
        // Add partial message if generation was stopped
        if (streamingMessage.value) {
          const assistantMessage: ChatMessage = {
            id: Date.now(),
            type: 'assistant',
            content: streamingMessage.value + ' [Generation stopped]',
            timestamp: new Date()
          }
          messages.value.push(assistantMessage)
        }
      } else {
        console.error('Failed to send streaming message:', error)
        throw error
      }
    } finally {
      isStreaming.value = false
      streamingMessage.value = ''
      streamController.value = null
    }
  }
  
  function stopStreaming() {
    if (streamController.value) {
      streamController.value.abort()
    }
  }
  
  async function loadChatHistory() {
    try {
      const response = await chatApi.getChatHistory()
      messages.value = response.messages
      currentSession.value = response.session
    } catch (error) {
      console.error('Failed to load chat history:', error)
    }
  }
  
  async function clearChatHistory() {
    try {
      await chatApi.clearChatHistory()
      messages.value = []
      currentSession.value = null
    } catch (error) {
      console.error('Failed to clear chat history:', error)
      throw error
    }
  }
  
  function startNewSession() {
    messages.value = []
    currentSession.value = null
  }
  
  return {
    // State
    messages,
    currentSession,
    sessions,
    isLoading,
    isStreaming,
    streamingMessage,
    
    // Getters
    lastMessage,
    hasMessages,
    
    // Actions
    sendMessage,
    sendStreamingMessage,
    loadChatHistory,
    clearChatHistory,
    startNewSession,
    stopStreaming
  }
})