<template>
  <div class="w-full max-w-md mx-auto">
    <Card>
      <CardHeader class="space-y-1">
        <CardTitle class="text-2xl font-bold text-center">Sign In</CardTitle>
        <p class="text-sm text-gray-600 text-center">
          Enter your email and password to access your account
        </p>
      </CardHeader>
      
      <CardContent>
        <form @submit.prevent="handleSubmit" class="space-y-4">
          <div class="space-y-2">
            <label for="email" class="text-sm font-medium text-gray-700">
              Email
            </label>
            <input
              id="email"
              v-model="form.email"
              type="email"
              placeholder="Enter your email"
              :disabled="isLoading"
              required
              class="w-full flex h-10 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              :class="{ 'border-red-500': emailError }"
            />
            <p v-if="emailError" class="text-sm text-red-600">{{ emailError }}</p>
          </div>

          <div class="space-y-2">
            <label for="password" class="text-sm font-medium text-gray-700">
              Password
            </label>
            <input
              id="password"
              v-model="form.password"
              type="password"
              placeholder="Enter your password"
              :disabled="isLoading"
              required
              class="w-full flex h-10 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              :class="{ 'border-red-500': passwordError }"
            />
            <p v-if="passwordError" class="text-sm text-red-600">{{ passwordError }}</p>
          </div>

          <div v-if="loginError" class="p-3 bg-red-50 border border-red-200 rounded-md">
            <p class="text-sm text-red-800">{{ loginError }}</p>
          </div>


          <Button
            type="submit"
            :disabled="isLoading || !isFormValid"
            class="w-full"
          >
            <span v-if="isLoading" class="flex items-center justify-center">
              <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Signing in...
            </span>
            <span v-else>Sign In</span>
          </Button>

          <div class="text-center">
            <p class="text-sm text-gray-600">
              Don't have an account?
              <button
                type="button"
                @click="$emit('switch-to-register')"
                class="text-blue-600 hover:text-blue-500 font-medium"
              >
                Sign up
              </button>
            </p>
          </div>
        </form>
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Button from '@/components/ui/Button.vue'

// Emits
defineEmits<{
  'switch-to-register': []
}>()

// Router and stores
const router = useRouter()
const authStore = useAuthStore()

// Form state
const form = ref({
  email: '',
  password: ''
})

// Form validation
const emailError = ref('')
const passwordError = ref('')

const isFormValid = computed(() => {
  return form.value.email.trim() !== '' && 
         form.value.password.trim() !== ''
})

const isLoading = computed(() => authStore.isLoading)
const loginError = computed(() => authStore.loginError)

// Validation functions
function isValidEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRegex.test(email)
}

function validateForm(): boolean {
  let isValid = true
  
  // Reset errors
  emailError.value = ''
  passwordError.value = ''
  
  // Validate email
  if (!form.value.email.trim()) {
    emailError.value = 'Email is required'
    isValid = false
  } else if (!isValidEmail(form.value.email)) {
    emailError.value = 'Please enter a valid email address'
    isValid = false
  }
  
  // Validate password
  if (!form.value.password.trim()) {
    passwordError.value = 'Password is required'
    isValid = false
  }
  
  return isValid
}

// Form submission
async function handleSubmit() {
  if (!validateForm()) return
  
  authStore.clearErrors()
  
  const success = await authStore.login({
    email: form.value.email.trim(),
    password: form.value.password
  })
  
  if (success) {
    // Redirect to dashboard or previous page
    const redirectTo = router.currentRoute.value.query.redirect as string || '/'
    router.push(redirectTo)
  }
}
</script>
