import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/auth'
import { useAppStore } from './app'
import type { User, UserCreate, UserLogin, AuthState } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref<User | null>(null)
  const token = ref<string | null>(null)
  const isLoading = ref(false)
  const loginError = ref<string | null>(null)
  const registerError = ref<string | null>(null)

  // Getters
  const isAuthenticated = computed(() => !!token.value && !!user.value)
  const isAdmin = computed(() => user.value?.is_superuser || false)
  
  const authState = computed((): AuthState => ({
    user: user.value,
    token: token.value,
    isAuthenticated: isAuthenticated.value,
    isLoading: isLoading.value
  }))

  // Actions
  async function register(userData: UserCreate): Promise<boolean> {
    const appStore = useAppStore()
    isLoading.value = true
    registerError.value = null

    try {
      await authApi.register(userData)
      
      appStore.addNotification({
        type: 'success',
        title: 'Registration Successful',
        message: 'Your account has been created successfully. Please log in.',
      })
      
      return true
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Registration failed'
      registerError.value = errorMessage
      
      appStore.addNotification({
        type: 'error',
        title: 'Registration Failed',
        message: errorMessage,
      })
      
      return false
    } finally {
      isLoading.value = false
    }
  }

  async function login(userData: UserLogin): Promise<boolean> {
    const appStore = useAppStore()
    isLoading.value = true
    loginError.value = null

    try {
      const tokenData = await authApi.login(userData)
      
      // Store token
      token.value = tokenData.access_token
      authApi.setToken(tokenData.access_token)
      
      // Get user info
      await getCurrentUser()
      
      appStore.addNotification({
        type: 'success',
        title: 'Login Successful',
        message: `Welcome back, ${user.value?.email}!`,
      })
      
      return true
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Login failed'
      loginError.value = errorMessage
      
      appStore.addNotification({
        type: 'error',
        title: 'Login Failed',
        message: errorMessage,
      })
      
      return false
    } finally {
      isLoading.value = false
    }
  }

  async function getCurrentUser(): Promise<void> {
    if (!token.value) return

    try {
      const userData = await authApi.getCurrentUser()
      user.value = userData
      authApi.setStoredUser(userData)
    } catch (error: any) {
      console.error('Failed to get current user:', error)
      // If getting user fails, clear auth state
      logout()
    }
  }

  function logout(): void {
    const appStore = useAppStore()
    
    user.value = null
    token.value = null
    loginError.value = null
    registerError.value = null
    
    authApi.logout()
    
    appStore.addNotification({
      type: 'info',
      title: 'Logged Out',
      message: 'You have been successfully logged out.',
    })
  }

  async function initializeAuth(): Promise<void> {
    // Check for stored token and user data
    const storedToken = authApi.getToken()
    const storedUser = authApi.getStoredUser()

    if (storedToken && storedUser) {
      token.value = storedToken
      user.value = storedUser
      
      // Verify token is still valid by getting current user
      try {
        await getCurrentUser()
      } catch (error) {
        // Token is invalid, clear auth state
        logout()
      }
    }
  }

  function clearErrors(): void {
    loginError.value = null
    registerError.value = null
  }

  return {
    // State
    user,
    token,
    isLoading,
    loginError,
    registerError,
    
    // Getters
    isAuthenticated,
    isAdmin,
    authState,
    
    // Actions
    register,
    login,
    getCurrentUser,
    logout,
    initializeAuth,
    clearErrors
  }
})
