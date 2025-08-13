import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { AppConfig, NotificationMessage } from '@/types'

export const useAppStore = defineStore('app', () => {
  // State
  const config = ref<AppConfig | null>(null)
  const notifications = ref<NotificationMessage[]>([])
  const isOnline = ref(navigator.onLine)
  const theme = ref<'light' | 'dark'>('light')
  const sidebarCollapsed = ref(false)
  
  // Getters
  const hasNotifications = computed(() => notifications.value.length > 0)
  const unreadNotifications = computed(() => 
    notifications.value.filter(n => !n.read)
  )
  
  // Actions
  function addNotification(notification: Omit<NotificationMessage, 'id' | 'timestamp' | 'read'>) {
    const newNotification: NotificationMessage = {
      ...notification,
      id: Date.now(),
      timestamp: new Date(),
      read: false
    }
    
    notifications.value.unshift(newNotification)
    
    // Auto-remove after 5 seconds for success messages
    if (notification.type === 'success') {
      setTimeout(() => {
        removeNotification(newNotification.id)
      }, 5000)
    }
  }
  
  function removeNotification(id: number) {
    notifications.value = notifications.value.filter(n => n.id !== id)
  }
  
  function markNotificationAsRead(id: number) {
    const notification = notifications.value.find(n => n.id === id)
    if (notification) {
      notification.read = true
    }
  }
  
  function toggleTheme() {
    theme.value = theme.value === 'light' ? 'dark' : 'light'
    localStorage.setItem('theme', theme.value)
  }
  
  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
    localStorage.setItem('sidebarCollapsed', String(sidebarCollapsed.value))
  }
  
  function setOnlineStatus(online: boolean) {
    isOnline.value = online
  }
  
  // Initialize from localStorage
  function initializeFromStorage() {
    const savedTheme = localStorage.getItem('theme') as 'light' | 'dark'
    if (savedTheme) {
      theme.value = savedTheme
    }
    
    const savedSidebarState = localStorage.getItem('sidebarCollapsed')
    if (savedSidebarState) {
      sidebarCollapsed.value = savedSidebarState === 'true'
    }
    
    // Initialize default config
    if (!config.value) {
      config.value = {
        apiBaseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api',
        maxFileSize: 50 * 1024 * 1024, // 50MB
        supportedFileTypes: ['pdf', 'docx', 'txt', 'md', 'pptx', 'xlsx', 'csv', 'rtf'],
        features: {
          webScraping: true,
          streaming: true,
          multipleFiles: true
        }
      }
    }
  }
  
  return {
    // State
    config,
    notifications,
    isOnline,
    theme,
    sidebarCollapsed,
    
    // Getters
    hasNotifications,
    unreadNotifications,
    
    // Actions
    addNotification,
    removeNotification,
    markNotificationAsRead,
    toggleTheme,
    toggleSidebar,
    setOnlineStatus,
    initializeFromStorage
  }
})