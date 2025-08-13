<template>
  <div class="w-full max-w-md mx-auto">
    <Card>
      <CardHeader class="space-y-1">
        <CardTitle class="text-2xl font-bold text-center">Create Account</CardTitle>
        <p class="text-sm text-gray-600 text-center">
          Enter your information to create a new account
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
              placeholder="Create a password"
              :disabled="isLoading"
              required
              class="w-full flex h-10 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              :class="{ 'border-red-500': passwordError }"
            />
            <p v-if="passwordError" class="text-sm text-red-600">{{ passwordError }}</p>
          </div>

          <div class="space-y-2">
            <label for="confirmPassword" class="text-sm font-medium text-gray-700">
              Confirm Password
            </label>
            <input
              id="confirmPassword"
              v-model="form.confirmPassword"
              type="password"
              placeholder="Confirm your password"
              :disabled="isLoading"
              required
              class="w-full flex h-10 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              :class="{ 'border-red-500': confirmPasswordError }"
            />
            <p v-if="confirmPasswordError" class="text-sm text-red-600">{{ confirmPasswordError }}</p>
          </div>

          <!-- Password requirements -->
          <div class="text-xs text-gray-600 space-y-1">
            <p>Password must contain:</p>
            <ul class="list-disc list-inside space-y-1">
              <li :class="{ 'text-green-600': hasMinLength }">At least 8 characters</li>
              <li :class="{ 'text-green-600': hasUppercase }">One uppercase letter</li>
              <li :class="{ 'text-green-600': hasLowercase }">One lowercase letter</li>
              <li :class="{ 'text-green-600': hasNumber }">One number</li>
            </ul>
          </div>

          <div v-if="registerError" class="p-3 bg-red-50 border border-red-200 rounded-md">
            <p class="text-sm text-red-800">{{ registerError }}</p>
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
              Creating account...
            </span>
            <span v-else>Create Account</span>
          </Button>

          <div class="text-center">
            <p class="text-sm text-gray-600">
              Already have an account?
              <button
                type="button"
                @click="$emit('switch-to-login')"
                class="text-blue-600 hover:text-blue-500 font-medium"
              >
                Sign in
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
import { useAuthStore } from '@/stores/auth'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Button from '@/components/ui/Button.vue'

// Emits
const emit = defineEmits<{
  'switch-to-login': []
  'registration-success': []
}>()

// Store
const authStore = useAuthStore()

// Form state
const form = ref({
  email: '',
  password: '',
  confirmPassword: ''
})

// Form validation
const emailError = ref('')
const passwordError = ref('')
const confirmPasswordError = ref('')

// Password strength indicators
const hasMinLength = computed(() => form.value.password.length >= 8)
const hasUppercase = computed(() => /[A-Z]/.test(form.value.password))
const hasLowercase = computed(() => /[a-z]/.test(form.value.password))
const hasNumber = computed(() => /\d/.test(form.value.password))

const isPasswordStrong = computed(() => {
  return hasMinLength.value && hasUppercase.value && hasLowercase.value && hasNumber.value
})

const isFormValid = computed(() => {
  return form.value.email.trim() !== '' && 
         form.value.password.trim() !== '' &&
         form.value.confirmPassword.trim() !== ''
})

const isLoading = computed(() => authStore.isLoading)
const registerError = computed(() => authStore.registerError)

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
  confirmPasswordError.value = ''
  
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
  } else if (!isPasswordStrong.value) {
    passwordError.value = 'Password does not meet requirements'
    isValid = false
  }
  
  // Validate password confirmation
  if (!form.value.confirmPassword.trim()) {
    confirmPasswordError.value = 'Please confirm your password'
    isValid = false
  } else if (form.value.password !== form.value.confirmPassword) {
    confirmPasswordError.value = 'Passwords do not match'
    isValid = false
  }
  
  return isValid
}

// Form submission
async function handleSubmit() {
  if (!validateForm()) return
  
  authStore.clearErrors()
  
  const success = await authStore.register({
    email: form.value.email.trim(),
    password: form.value.password
  })
  
  if (success) {
    // Reset form
    form.value = {
      email: '',
      password: '',
      confirmPassword: ''
    }
    
    // Emit success event to switch to login
    emit('registration-success')
  }
}
</script>
