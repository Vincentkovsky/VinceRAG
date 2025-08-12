<template>
  <div class="space-y-6">
    <h1 class="text-3xl font-bold">Settings</h1>

    <Card class="p-6">
      <h2 class="text-xl font-semibold mb-4">Appearance</h2>
      <div class="space-y-4">
        <div class="flex items-center justify-between">
          <div>
            <label class="text-sm font-medium">Theme</label>
            <p class="text-sm text-muted-foreground">Choose your preferred theme</p>
          </div>
          <Button
            variant="outline"
            @click="appStore.toggleTheme()"
          >
            {{ appStore.theme === 'light' ? 'Switch to Dark' : 'Switch to Light' }}
          </Button>
        </div>
      </div>
    </Card>

    <Card class="p-6">
      <h2 class="text-xl font-semibold mb-4">System Status</h2>
      <div class="space-y-4">
        <div class="flex items-center justify-between">
          <span class="text-sm font-medium">Connection Status</span>
          <Badge :variant="appStore.isOnline ? 'success' : 'destructive'">
            {{ appStore.isOnline ? 'Online' : 'Offline' }}
          </Badge>
        </div>
        
        <div class="flex items-center justify-between">
          <span class="text-sm font-medium">Total Documents</span>
          <Badge variant="secondary">
            {{ documentsStore.totalDocuments }}
          </Badge>
        </div>
        
        <div class="flex items-center justify-between">
          <span class="text-sm font-medium">Processed Documents</span>
          <Badge variant="success">
            {{ documentsStore.completedDocuments }}
          </Badge>
        </div>
      </div>
    </Card>

    <Card class="p-6">
      <h2 class="text-xl font-semibold mb-4">Actions</h2>
      <div class="space-y-4">
        <Button
          variant="outline"
          @click="clearChatHistory"
          :disabled="!chatStore.hasMessages"
        >
          Clear Chat History
        </Button>
      </div>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { useAppStore } from '@/stores/app'
import { useDocumentsStore } from '@/stores/documents'
import { useChatStore } from '@/stores/chat'
import Card from '@/components/ui/Card.vue'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'

const appStore = useAppStore()
const documentsStore = useDocumentsStore()
const chatStore = useChatStore()

async function clearChatHistory() {
  try {
    await chatStore.clearChatHistory()
    appStore.addNotification({
      type: 'success',
      title: 'Success',
      message: 'Chat history cleared successfully'
    })
  } catch (error) {
    appStore.addNotification({
      type: 'error',
      title: 'Error',
      message: 'Failed to clear chat history'
    })
  }
}
</script>