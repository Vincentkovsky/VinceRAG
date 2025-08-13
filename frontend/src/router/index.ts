import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/documents'
  },
  {
    path: '/auth',
    name: 'Auth',
    component: () => import('@/views/AuthView.vue'),
    meta: {
      title: 'Authentication',
      requiresGuest: true // Only accessible when not authenticated
    }
  },
  {
    path: '/documents',
    name: 'Documents',
    component: () => import('@/views/DocumentsView.vue'),
    meta: {
      title: 'Document Management',
      requiresAuth: true
    }
  },
  {
    path: '/chat',
    name: 'Chat',
    component: () => import('@/views/ChatView.vue'),
    meta: {
      title: 'Chat Interface',
      requiresAuth: true
    }
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/SettingsView.vue'),
    meta: {
      title: 'Settings',
      requiresAuth: true
    }
  },
  {
    path: '/admin',
    name: 'Admin',
    component: () => import('@/views/AdminView.vue'),
    meta: {
      title: 'Admin Dashboard',
      requiresAuth: true,
      requiresAdmin: true
    }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Navigation guards
router.beforeEach(async (to, _from, next) => {
  // Update document title
  if (to.meta?.title) {
    document.title = `${to.meta.title} - KiroRAG`
  } else {
    document.title = 'KiroRAG'
  }
  
  const authStore = useAuthStore()
  
  // Initialize auth state if not already done
  if (!authStore.user && !authStore.isLoading) {
    await authStore.initializeAuth()
  }
  
  // Check if route requires authentication
  if (to.meta?.requiresAuth && !authStore.isAuthenticated) {
    // Redirect to auth page with return URL
    next({
      name: 'Auth',
      query: { redirect: to.fullPath }
    })
    return
  }
  
  // Check if route requires admin privileges
  if (to.meta?.requiresAdmin && !authStore.isAdmin) {
    // Redirect to documents page if not admin
    next({ name: 'Documents' })
    return
  }
  
  // Check if route is for guests only (like auth page)
  if (to.meta?.requiresGuest && authStore.isAuthenticated) {
    // Redirect to documents page if already authenticated
    next({ name: 'Documents' })
    return
  }
  
  next()
})

export default router