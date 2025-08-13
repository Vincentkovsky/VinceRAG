<template>
  <div class="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
    <!-- Header -->
    <div class="sm:mx-auto sm:w-full sm:max-w-md">
      <div class="text-center">
        <h1 class="text-3xl font-bold text-gray-900 mb-2">KiroRAG</h1>
        <p class="text-sm text-gray-600">
          Intelligent Document Search & Chat Platform
        </p>
      </div>
    </div>

    <!-- Auth Forms -->
    <div class="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
      <div class="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10">
        <!-- Login Form -->
        <LoginForm 
          v-if="currentView === 'login'"
          @switch-to-register="switchToRegister"
        />
        
        <!-- Register Form -->
        <RegisterForm 
          v-else-if="currentView === 'register'"
          @switch-to-login="switchToLogin"
          @registration-success="handleRegistrationSuccess"
        />
        
        <!-- Success Message -->
        <div v-else-if="currentView === 'success'" class="text-center space-y-4">
          <div class="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100">
            <svg class="h-6 w-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <div>
            <h3 class="text-lg font-medium text-gray-900">Registration Successful!</h3>
            <p class="mt-2 text-sm text-gray-600">
              Your account has been created successfully. You can now sign in with your credentials.
            </p>
          </div>
          <Button @click="switchToLogin" class="w-full">
            Continue to Sign In
          </Button>
        </div>
      </div>
      
      <!-- Footer -->
      <div class="mt-8 text-center">
        <p class="text-xs text-gray-500">
          By signing in, you agree to our 
          <a href="#" class="text-blue-600 hover:text-blue-500">Terms of Service</a>
          and 
          <a href="#" class="text-blue-600 hover:text-blue-500">Privacy Policy</a>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import LoginForm from '@/components/auth/LoginForm.vue'
import RegisterForm from '@/components/auth/RegisterForm.vue'
import Button from '@/components/ui/Button.vue'

// Router and stores
const router = useRouter()
const authStore = useAuthStore()

// View state
const currentView = ref<'login' | 'register' | 'success'>('login')

// Check if user is already authenticated
onMounted(() => {
  if (authStore.isAuthenticated) {
    router.push('/')
  }
})

// View switching functions
function switchToLogin() {
  currentView.value = 'login'
  authStore.clearErrors()
}

function switchToRegister() {
  currentView.value = 'register'
  authStore.clearErrors()
}

function handleRegistrationSuccess() {
  currentView.value = 'success'
}
</script>
