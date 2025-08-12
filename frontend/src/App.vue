<template>
  <div id="app" class="min-h-screen bg-background">
    <!-- Navigation -->
    <nav class="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div class="container flex h-14 items-center">
        <div class="mr-4 flex">
          <router-link to="/" class="mr-6 flex items-center space-x-2">
            <span class="font-bold">RAG System</span>
          </router-link>
        </div>
        
        <div class="flex flex-1 items-center justify-between space-x-2 md:justify-end">
          <nav class="flex items-center space-x-6">
            <router-link
              to="/documents"
              class="text-sm font-medium transition-colors hover:text-primary"
              :class="{ 'text-primary': $route.name === 'Documents' }"
            >
              Documents
            </router-link>
            <router-link
              to="/chat"
              class="text-sm font-medium transition-colors hover:text-primary"
              :class="{ 'text-primary': $route.name === 'Chat' }"
            >
              Chat
            </router-link>
            <router-link
              to="/settings"
              class="text-sm font-medium transition-colors hover:text-primary"
              :class="{ 'text-primary': $route.name === 'Settings' }"
            >
              Settings
            </router-link>
          </nav>
          
          <Button
            variant="ghost"
            size="icon"
            @click="appStore.toggleTheme()"
            class="ml-4"
          >
            <span v-if="appStore.theme === 'light'">🌙</span>
            <span v-else>☀️</span>
          </Button>
        </div>
      </div>
    </nav>

    <!-- Main content -->
    <main class="container mx-auto py-6">
      <router-view />
    </main>

    <!-- Notifications -->
    <div class="fixed bottom-4 right-4 z-50 space-y-2">
      <div
        v-for="notification in appStore.notifications"
        :key="notification.id"
        class="max-w-sm rounded-lg border bg-background p-4 shadow-lg"
        :class="{
          'border-green-500': notification.type === 'success',
          'border-red-500': notification.type === 'error',
          'border-yellow-500': notification.type === 'warning',
          'border-blue-500': notification.type === 'info',
        }"
      >
        <div class="flex items-start justify-between">
          <div class="flex-1">
            <h4 class="font-medium">{{ notification.title }}</h4>
            <p class="text-sm text-muted-foreground">{{ notification.message }}</p>
          </div>
          <Button
            variant="ghost"
            size="icon"
            @click="appStore.removeNotification(notification.id)"
            class="h-6 w-6"
          >
            ✕
          </Button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { useAppStore } from '@/stores/app'
import Button from '@/components/ui/Button.vue'

const appStore = useAppStore()

onMounted(() => {
  appStore.initializeFromStorage()
  
  // Listen for online/offline events
  window.addEventListener('online', () => appStore.setOnlineStatus(true))
  window.addEventListener('offline', () => appStore.setOnlineStatus(false))
})

// Apply theme to document
watch(
  () => appStore.theme,
  (theme) => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  },
  { immediate: true }
)
</script>