<template>
  <div class="space-y-4">
    <!-- URL Input -->
    <div class="flex gap-2">
      <div class="flex-1">
        <Input
          v-model="url"
          placeholder="Enter website URL (e.g., https://example.com)"
          :class="{ 'border-destructive': urlError }"
          @input="validateUrl"
          @keyup.enter="addUrl"
        />
        <p v-if="urlError" class="text-sm text-destructive mt-1">
          {{ urlError }}
        </p>
      </div>
      
      <Button
        @click="addUrl"
        :disabled="!isValidUrl || isProcessing"
      >
        {{ isProcessing ? 'Adding...' : 'Add URL' }}
      </Button>
    </div>

    <!-- Crawling Options -->
    <div class="border rounded-lg p-4 space-y-4">
      <h3 class="font-medium">Crawling Options</h3>
      
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label class="block text-sm font-medium mb-1">
            Max Depth
          </label>
          <select
            v-model="crawlOptions.maxDepth"
            class="w-full px-3 py-2 border border-input rounded-md bg-background text-sm"
          >
            <option :value="1">1 (Current page only)</option>
            <option :value="2">2 (1 level deep)</option>
            <option :value="3">3 (2 levels deep)</option>
          </select>
          <p class="text-xs text-muted-foreground mt-1">
            How deep to crawl linked pages
          </p>
        </div>
        
        <div>
          <label class="block text-sm font-medium mb-1">
            Max Pages
          </label>
          <select
            v-model="crawlOptions.maxPages"
            class="w-full px-3 py-2 border border-input rounded-md bg-background text-sm"
          >
            <option :value="1">1 page</option>
            <option :value="5">5 pages</option>
            <option :value="10">10 pages</option>
            <option :value="25">25 pages</option>
            <option :value="50">50 pages</option>
          </select>
          <p class="text-xs text-muted-foreground mt-1">
            Maximum pages to crawl
          </p>
        </div>
        
        <div>
          <label class="flex items-center space-x-2">
            <input
              v-model="crawlOptions.includeSubdomains"
              type="checkbox"
              class="rounded border-input"
            />
            <span class="text-sm font-medium">Include Subdomains</span>
          </label>
          <p class="text-xs text-muted-foreground mt-1">
            Crawl pages from subdomains
          </p>
        </div>
      </div>
    </div>

    <!-- URL Preview -->
    <div v-if="urlPreview" class="border rounded-lg p-4">
      <h3 class="font-medium mb-3">Preview</h3>
      <div class="flex items-start space-x-3">
        <div class="text-2xl">🌐</div>
        <div class="flex-1 min-w-0">
          <h4 class="font-medium truncate">{{ urlPreview.title || 'Loading...' }}</h4>
          <p class="text-sm text-muted-foreground truncate">{{ urlPreview.url }}</p>
          <p v-if="urlPreview.description" class="text-sm mt-1 line-clamp-2">
            {{ urlPreview.description }}
          </p>
          <div v-if="urlPreview.metadata" class="flex flex-wrap gap-2 mt-2">
            <Badge v-if="urlPreview.metadata.domain" variant="outline" class="text-xs">
              {{ urlPreview.metadata.domain }}
            </Badge>
            <Badge v-if="urlPreview.metadata.language" variant="outline" class="text-xs">
              {{ urlPreview.metadata.language }}
            </Badge>
          </div>
        </div>
      </div>
    </div>

    <!-- Batch URL Processing -->
    <div class="border rounded-lg p-4">
      <h3 class="font-medium mb-3">Batch URL Processing</h3>
      <div class="space-y-3">
        <textarea
          v-model="batchUrls"
          placeholder="Enter multiple URLs, one per line..."
          rows="4"
          class="w-full px-3 py-2 border border-input rounded-md bg-background text-sm resize-none"
        />
        
        <div class="flex justify-between items-center">
          <p class="text-sm text-muted-foreground">
            {{ batchUrlList.length }} URLs detected
          </p>
          <Button
            @click="processBatchUrls"
            :disabled="batchUrlList.length === 0 || isProcessing"
            variant="outline"
          >
            Process All URLs
          </Button>
        </div>
      </div>
    </div>

    <!-- Processing Status -->
    <div v-if="processingUrls.length > 0" class="space-y-3">
      <h3 class="font-medium">Processing URLs</h3>
      <div
        v-for="urlStatus in processingUrls"
        :key="urlStatus.id"
        class="flex items-center space-x-3 p-3 border rounded-lg"
      >
        <div class="flex-1">
          <div class="flex items-center justify-between mb-1">
            <span class="text-sm font-medium truncate">{{ urlStatus.url }}</span>
            <Badge
              :variant="
                urlStatus.status === 'completed' ? 'success' :
                urlStatus.status === 'failed' ? 'destructive' :
                'secondary'
              "
            >
              {{ urlStatus.status }}
            </Badge>
          </div>
          
          <div v-if="urlStatus.status === 'processing'" class="space-y-1">
            <Progress :value="urlStatus.progress" class="h-2" />
            <p class="text-xs text-muted-foreground">
              {{ urlStatus.message || 'Processing...' }}
            </p>
          </div>
          
          <div v-if="urlStatus.metadata" class="text-xs text-muted-foreground mt-1">
            <span v-if="urlStatus.metadata.pagesFound">
              {{ urlStatus.metadata.pagesFound }} pages found
            </span>
            <span v-if="urlStatus.metadata.pagesProcessed">
              • {{ urlStatus.metadata.pagesProcessed }} processed
            </span>
          </div>
        </div>
        
        <Button
          v-if="urlStatus.status === 'failed' || urlStatus.status === 'completed'"
          variant="ghost"
          size="icon"
          @click="removeProcessingUrl(urlStatus.id)"
        >
          ✕
        </Button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useDocumentsStore } from '@/stores/documents'
import { useAppStore } from '@/stores/app'
import type { CrawlOptions } from '@/types'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Badge from '@/components/ui/Badge.vue'
import Progress from '@/components/ui/Progress.vue'

interface UrlPreview {
  url: string
  title?: string
  description?: string
  metadata?: {
    domain?: string
    language?: string
    publishedDate?: string
  }
}

interface ProcessingUrl {
  id: string
  url: string
  status: 'processing' | 'completed' | 'failed'
  progress: number
  message?: string
  metadata?: {
    pagesFound?: number
    pagesProcessed?: number
  }
}

const documentsStore = useDocumentsStore()
const appStore = useAppStore()

const url = ref('')
const urlError = ref('')
const urlPreview = ref<UrlPreview | null>(null)
const isProcessing = ref(false)
const batchUrls = ref('')
const processingUrls = ref<ProcessingUrl[]>([])

const crawlOptions = ref<CrawlOptions>({
  maxDepth: 2,
  maxPages: 10,
  includeSubdomains: false
})

const isValidUrl = computed(() => {
  return url.value && !urlError.value
})

const batchUrlList = computed(() => {
  return batchUrls.value
    .split('\n')
    .map(u => u.trim())
    .filter(u => u && isValidUrlString(u))
})

function isValidUrlString(urlString: string): boolean {
  try {
    const urlObj = new URL(urlString)
    return urlObj.protocol === 'http:' || urlObj.protocol === 'https:'
  } catch {
    return false
  }
}

function validateUrl() {
  urlError.value = ''
  urlPreview.value = null
  
  if (!url.value) return
  
  if (!isValidUrlString(url.value)) {
    urlError.value = 'Please enter a valid URL starting with http:// or https://'
    return
  }
  
  // Generate preview
  generateUrlPreview()
}

function generateUrlPreview() {
  if (!url.value) return
  
  try {
    const urlObj = new URL(url.value)
    urlPreview.value = {
      url: url.value,
      title: `Preview for ${urlObj.hostname}`,
      description: 'Click "Add URL" to fetch and process this page',
      metadata: {
        domain: urlObj.hostname
      }
    }
  } catch (error) {
    console.error('Error generating preview:', error)
  }
}

async function addUrl() {
  if (!isValidUrl.value) return
  
  isProcessing.value = true
  
  try {
    const processingUrl: ProcessingUrl = {
      id: `${url.value}-${Date.now()}`,
      url: url.value,
      status: 'processing',
      progress: 0
    }
    
    processingUrls.value.push(processingUrl)
    
    await documentsStore.addUrl(url.value, crawlOptions.value)
    
    processingUrl.status = 'completed'
    processingUrl.progress = 100
    
    appStore.addNotification({
      type: 'success',
      title: 'URL Added',
      message: `Successfully added ${url.value}`
    })
    
    // Clear form
    url.value = ''
    urlPreview.value = null
    
  } catch (error) {
    const processingUrl = processingUrls.value.find(p => p.url === url.value)
    if (processingUrl) {
      processingUrl.status = 'failed'
    }
    
    appStore.addNotification({
      type: 'error',
      title: 'Failed to Add URL',
      message: `Could not process ${url.value}`
    })
  } finally {
    isProcessing.value = false
  }
}

async function processBatchUrls() {
  if (batchUrlList.value.length === 0) return
  
  isProcessing.value = true
  
  const batchProcessingUrls: ProcessingUrl[] = batchUrlList.value.map(url => ({
    id: `${url}-${Date.now()}`,
    url,
    status: 'processing',
    progress: 0
  }))
  
  processingUrls.value.push(...batchProcessingUrls)
  
  // Process URLs sequentially to avoid overwhelming the server
  for (const processingUrl of batchProcessingUrls) {
    try {
      await documentsStore.addUrl(processingUrl.url, crawlOptions.value)
      
      processingUrl.status = 'completed'
      processingUrl.progress = 100
      
    } catch (error) {
      processingUrl.status = 'failed'
    }
  }
  
  const successCount = batchProcessingUrls.filter(p => p.status === 'completed').length
  const failCount = batchProcessingUrls.filter(p => p.status === 'failed').length
  
  appStore.addNotification({
    type: successCount > 0 ? 'success' : 'error',
    title: 'Batch Processing Complete',
    message: `${successCount} URLs processed successfully, ${failCount} failed`
  })
  
  // Clear batch input
  batchUrls.value = ''
  isProcessing.value = false
}

function removeProcessingUrl(id: string) {
  processingUrls.value = processingUrls.value.filter(p => p.id !== id)
}

// Watch for URL changes to trigger validation
watch(url, validateUrl)
</script>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>