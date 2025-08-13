<template>
  <div class="space-y-6">
    <div>
      <h3 class="text-lg font-medium">AI Model Configuration</h3>
      <p class="text-sm text-muted-foreground mt-1">
      </p>
    </div>

    <!-- Configuration Form -->
    <Card>
      <CardHeader>
        <CardTitle>Model Configuration</CardTitle>
        <p class="text-sm text-muted-foreground">
          Select different providers for embedding generation and chat responses
        </p>
      </CardHeader>
      <CardContent>
        <form @submit.prevent="saveConfiguration" class="space-y-8">
          
          <!-- Embedding Model Configuration -->
          <div class="space-y-4">
            <div class="border-l-4 border-blue-500 pl-4">
              <h4 class="text-lg font-medium text-blue-700">Embedding Model</h4>
              <p class="text-sm text-muted-foreground">Used for document processing and similarity search</p>
            </div>
            
            <div class="grid gap-4 md:grid-cols-2">
              <div class="md:col-span-2">
                <label class="text-sm font-medium">Embedding Provider</label>
                <select 
                  v-model="config.embedding_provider" 
                  class="w-full mt-1 rounded-md border border-input bg-background px-3 py-2"
                >
                  <option value="openai">OpenAI</option>
                  <option value="qwen">Qwen (Alibaba Cloud)</option>
                  <option value="custom">Custom API</option>
                </select>
              </div>

              <!-- OpenAI Embedding -->
              <template v-if="config.embedding_provider === 'openai'">
                <div>
                  <label class="text-sm font-medium">OpenAI API Key</label>
                  <input
                    v-model="config.openai_api_key"
                    type="password"
                    placeholder="sk-..."
                    class="w-full mt-1 rounded-md border border-input bg-background px-3 py-2"
                  />
                </div>
                <div>
                  <label class="text-sm font-medium">Base URL</label>
                  <input
                    v-model="config.openai_base_url"
                    type="url"
                    class="w-full mt-1 rounded-md border border-input bg-background px-3 py-2"
                  />
                </div>
                <div>
                  <label class="text-sm font-medium">Embedding Model</label>
                  <select 
                    v-model="config.openai_embedding_model"
                    class="w-full mt-1 rounded-md border border-input bg-background px-3 py-2"
                  >
                    <option value="text-embedding-ada-002">text-embedding-ada-002</option>
                    <option value="text-embedding-3-small">text-embedding-3-small</option>
                    <option value="text-embedding-3-large">text-embedding-3-large</option>
                    <option value="text-embedding-v4">text-embedding-v4</option>
                  </select>
                </div>
                <div>
                  <label class="text-sm font-medium">Embedding Dimensions</label>
                  <input
                    v-model.number="config.openai_embedding_dimensions"
                    type="number"
                    class="w-full mt-1 rounded-md border border-input bg-background px-3 py-2"
                  />
                </div>
              </template>

              <!-- Qwen Embedding -->
              <template v-if="config.embedding_provider === 'qwen'">
                <div>
                  <label class="text-sm font-medium">Qwen API Key</label>
                  <input
                    v-model="config.qwen_api_key"
                    type="password"
                    placeholder="sk-..."
                    class="w-full mt-1 rounded-md border border-input bg-background px-3 py-2"
                  />
                </div>
                <div>
                  <label class="text-sm font-medium">Base URL</label>
                  <input
                    v-model="config.qwen_base_url"
                    type="url"
                    class="w-full mt-1 rounded-md border border-input bg-background px-3 py-2"
                  />
                </div>
                <div>
                  <label class="text-sm font-medium">Embedding Model</label>
                  <select 
                    v-model="config.qwen_embedding_model"
                    class="w-full mt-1 rounded-md border border-input bg-background px-3 py-2"
                  >
                    <option value="text-embedding-v1">text-embedding-v1</option>
                    <option value="text-embedding-v2">text-embedding-v2</option>
                    <option value="text-embedding-v3">text-embedding-v3</option>
                    <option value="text-embedding-v4">text-embedding-v4</option>
                  </select>
                </div>
                <div>
                  <label class="text-sm font-medium">Embedding Dimensions</label>
                  <input
                    v-model.number="config.qwen_embedding_dimensions"
                    type="number"
                    class="w-full mt-1 rounded-md border border-input bg-background px-3 py-2"
                  />
                </div>
              </template>

              <!-- Custom Embedding -->
              <template v-if="config.embedding_provider === 'custom'">
                <div>
                  <label class="text-sm font-medium">API Key</label>
                  <input
                    v-model="config.custom_api_key"
                    type="password"
                    class="w-full mt-1 rounded-md border border-input bg-background px-3 py-2"
                  />
                </div>
                <div>
                  <label class="text-sm font-medium">Base URL</label>
                  <input
                    v-model="config.custom_base_url"
                    type="url"
                    class="w-full mt-1 rounded-md border border-input bg-background px-3 py-2"
                  />
                </div>
                <div>
                  <label class="text-sm font-medium">Embedding Model</label>
                  <input
                    v-model="config.custom_embedding_model"
                    type="text"
                    class="w-full mt-1 rounded-md border border-input bg-background px-3 py-2"
                  />
                </div>
                <div>
                  <label class="text-sm font-medium">Embedding Dimensions</label>
                  <input
                    v-model.number="config.custom_embedding_dimensions"
                    type="number"
                    class="w-full mt-1 rounded-md border border-input bg-background px-3 py-2"
                  />
                </div>
              </template>
            </div>
          </div>

          <!-- Divider -->
          <hr class="border-gray-200" />

          <!-- Chat Model Configuration -->
          <div class="space-y-4">
            <div class="border-l-4 border-green-500 pl-4">
              <h4 class="text-lg font-medium text-green-700">Chat Model</h4>
              <p class="text-sm text-muted-foreground">Used for generating responses and conversations</p>
            </div>
            
            <div class="grid gap-4 md:grid-cols-2">
              <div class="md:col-span-2">
                <label class="text-sm font-medium">Chat Provider</label>
                <select 
                  v-model="config.chat_provider" 
                  class="w-full mt-1 rounded-md border border-input bg-background px-3 py-2"
                >
                  <option value="openai">OpenAI</option>
                  <option value="qwen">Qwen (Alibaba Cloud)</option>
                  <option value="custom">Custom API</option>
                </select>
              </div>

              <!-- OpenAI Chat -->
              <template v-if="config.chat_provider === 'openai'">
                <div v-if="config.chat_provider !== config.embedding_provider">
                  <label class="text-sm font-medium">OpenAI API Key</label>
                  <input
                    v-model="config.openai_api_key"
                    type="password"
                    placeholder="sk-..."
                    class="w-full mt-1 rounded-md border border-input bg-background px-3 py-2"
                  />
                </div>
                <div v-if="config.chat_provider !== config.embedding_provider">
                  <label class="text-sm font-medium">Base URL</label>
                  <input
                    v-model="config.openai_base_url"
                    type="url"
                    class="w-full mt-1 rounded-md border border-input bg-background px-3 py-2"
                  />
                </div>
                <div class="md:col-span-2">
                  <label class="text-sm font-medium">Chat Model</label>
                  <select 
                    v-model="config.openai_chat_model"
                    class="w-full mt-1 rounded-md border border-input bg-background px-3 py-2"
                  >
                    <option value="gpt-3.5-turbo">gpt-3.5-turbo</option>
                    <option value="gpt-4-turbo-preview">gpt-4-turbo-preview</option>
                    <option value="gpt-4">gpt-4</option>
                    <option value="gpt-4o">gpt-4o</option>
                    <option value="gpt-4o-mini">gpt-4o-mini</option>
                  </select>
                </div>
              </template>

              <!-- Qwen Chat -->
              <template v-if="config.chat_provider === 'qwen'">
                <div v-if="config.chat_provider !== config.embedding_provider">
                  <label class="text-sm font-medium">Qwen API Key</label>
                  <input
                    v-model="config.qwen_api_key"
                    type="password"
                    placeholder="sk-..."
                    class="w-full mt-1 rounded-md border border-input bg-background px-3 py-2"
                  />
                </div>
                <div v-if="config.chat_provider !== config.embedding_provider">
                  <label class="text-sm font-medium">Base URL</label>
                  <input
                    v-model="config.qwen_base_url"
                    type="url"
                    class="w-full mt-1 rounded-md border border-input bg-background px-3 py-2"
                  />
                </div>
                <div class="md:col-span-2">
                  <label class="text-sm font-medium">Chat Model</label>
                  <select 
                    v-model="config.qwen_chat_model"
                    class="w-full mt-1 rounded-md border border-input bg-background px-3 py-2"
                  >
                    <option value="qwen-turbo-latest">qwen-turbo-latest</option>
                    <option value="qwen-plus-latest">qwen-plus-latest</option>
                    <option value="qwen-max-latest">qwen-max-latest</option>
                    <option value="qwen-long">qwen-long</option>
                  </select>
                </div>
              </template>

              <!-- Custom Chat -->
              <template v-if="config.chat_provider === 'custom'">
                <div v-if="config.chat_provider !== config.embedding_provider">
                  <label class="text-sm font-medium">API Key</label>
                  <input
                    v-model="config.custom_api_key"
                    type="password"
                    class="w-full mt-1 rounded-md border border-input bg-background px-3 py-2"
                  />
                </div>
                <div v-if="config.chat_provider !== config.embedding_provider">
                  <label class="text-sm font-medium">Base URL</label>
                  <input
                    v-model="config.custom_base_url"
                    type="url"
                    class="w-full mt-1 rounded-md border border-input bg-background px-3 py-2"
                  />
                </div>
                <div class="md:col-span-2">
                  <label class="text-sm font-medium">Chat Model</label>
                  <input
                    v-model="config.custom_chat_model"
                    type="text"
                    class="w-full mt-1 rounded-md border border-input bg-background px-3 py-2"
                  />
                </div>
              </template>
            </div>
          </div>

          <!-- Mixed Provider Notice -->
          <div v-if="config.embedding_provider !== config.chat_provider" class="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div class="flex items-start">
              <div class="flex-shrink-0">
                <svg class="h-5 w-5 text-blue-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
                </svg>
              </div>
              <div class="ml-3">
                <h3 class="text-sm font-medium text-blue-800">Mixed Provider Configuration</h3>
                <div class="mt-1 text-sm text-blue-700">
                  <p>You're using different providers for embedding ({{ config.embedding_provider }}) and chat ({{ config.chat_provider }}). This allows you to optimize for the best performance in each area.</p>
                </div>
              </div>
            </div>
          </div>

          <!-- Action Buttons -->
          <div class="flex gap-3">
            <Button type="button" variant="outline" @click="testConnection" :disabled="testing">
              <span v-if="testing">Testing...</span>
              <span v-else>Test Configuration</span>
            </Button>
            <Button type="submit" :disabled="saving">
              <span v-if="saving">Saving...</span>
              <span v-else>Save Configuration</span>
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>

    <!-- Test Results -->
    <Card v-if="testResult">
      <CardHeader>
        <CardTitle>Configuration Test Result</CardTitle>
      </CardHeader>
      <CardContent>
        <div v-if="testResult.success" class="text-green-600">
          <div class="font-medium">✅ Configuration Test Successful</div>
          <div class="text-sm mt-1">{{ testResult.message }}</div>
          <div v-if="testResult.embedding_dimensions" class="text-sm mt-1">
            Embedding dimensions: {{ testResult.embedding_dimensions }}
          </div>
        </div>
        <div v-else class="text-red-600">
          <div class="font-medium">❌ Configuration Test Failed</div>
          <div class="text-sm mt-1">{{ testResult.error }}</div>
        </div>
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { modelsApi, type AIModelConfig, type ModelTestResult } from '@/api/models'
import { useAppStore } from '@/stores/app'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardContent from '@/components/ui/CardContent.vue'

const appStore = useAppStore()

const config = ref<AIModelConfig>({
  embedding_provider: 'openai',
  chat_provider: 'openai',
  openai_base_url: 'https://api.openai.com/v1',
  openai_embedding_model: 'text-embedding-ada-002',
  openai_embedding_dimensions: 1536,
  openai_chat_model: 'gpt-3.5-turbo',
  qwen_base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
  qwen_embedding_model: 'text-embedding-v2',
  qwen_embedding_dimensions: 1536,
  qwen_chat_model: 'qwen-max-latest',
  custom_base_url: '',
  custom_embedding_model: '',
  custom_embedding_dimensions: 1536,
  custom_chat_model: ''
})

const testing = ref(false)
const saving = ref(false)
const testResult = ref<ModelTestResult | null>(null)

onMounted(async () => {
  try {
    // Load current configuration
    const configData = await modelsApi.getConfig()
    config.value = configData
  } catch (error) {
    console.error('Failed to load model configuration:', error)
    appStore.addNotification({
      type: 'error',
      title: 'Loading Failed',
      message: 'Failed to load model configuration'
    })
  }
})

async function testConnection() {
  testing.value = true
  testResult.value = null
  
  try {
    testResult.value = await modelsApi.testConnection(config.value)
  } catch (error) {
    testResult.value = {
      success: false,
      error: 'Network error occurred'
    }
  } finally {
    testing.value = false
  }
}

async function saveConfiguration() {
  saving.value = true
  
  try {
    await modelsApi.updateConfig(config.value)
    
    appStore.addNotification({
      type: 'success',
      title: 'Configuration Saved',
      message: 'AI model configuration has been updated successfully'
    })
    
  } catch (error) {
    console.error('Failed to save configuration:', error)
    appStore.addNotification({
      type: 'error',
      title: 'Save Failed',
      message: 'Failed to save model configuration'
    })
  } finally {
    saving.value = false
  }
}
</script>