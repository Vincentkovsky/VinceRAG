<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-3xl font-bold">Chat Interface</h1>
      <Button
        variant="outline"
        @click="chatStore.startNewSession()"
        :disabled="!chatStore.hasMessages"
      >
        New Chat
      </Button>
    </div>

    <Card class="h-[600px] flex flex-col">
      <!-- Chat Messages -->
      <div class="flex-1 p-4 overflow-y-auto">
        <div v-if="!chatStore.hasMessages" class="flex items-center justify-center h-full text-muted-foreground">
          <div class="text-center">
            <p class="text-lg mb-2">Welcome to RAG System Chat</p>
            <p>Ask questions about your uploaded documents and web content.</p>
          </div>
        </div>
        
        <div v-else class="space-y-4">
          <div
            v-for="message in chatStore.messages"
            :key="message.id"
            class="flex"
            :class="message.type === 'user' ? 'justify-end' : 'justify-start'"
          >
            <div
              class="max-w-[80%] rounded-lg p-3"
              :class="
                message.type === 'user'
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted'
              "
            >
              <p class="whitespace-pre-wrap">{{ message.content }}</p>
              
              <!-- Sources for assistant messages -->
              <div v-if="message.sources && message.sources.length > 0" class="mt-3 pt-3 border-t border-border/50">
                <p class="text-xs font-medium mb-2">Sources:</p>
                <div class="space-y-1">
                  <div
                    v-for="source in message.sources"
                    :key="source.chunkId"
                    class="text-xs p-2 rounded bg-background/50"
                  >
                    <div class="font-medium">{{ source.documentName }}</div>
                    <div class="text-muted-foreground truncate">{{ source.chunk }}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Streaming message -->
          <div v-if="chatStore.isStreaming" class="flex justify-start">
            <div class="max-w-[80%] rounded-lg p-3 bg-muted">
              <p class="whitespace-pre-wrap">{{ chatStore.streamingMessage }}</p>
              <div class="mt-2">
                <div class="animate-pulse">Typing...</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Chat Input -->
      <div class="border-t p-4">
        <ChatInput />
      </div>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useChatStore } from '@/stores/chat'
import Card from '@/components/ui/Card.vue'
import Button from '@/components/ui/Button.vue'
import ChatInput from '@/components/chat/ChatInput.vue'

const chatStore = useChatStore()

onMounted(() => {
  chatStore.loadChatHistory()
})
</script>