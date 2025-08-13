<template>
  <div class="space-y-4">
    <!-- Search Input -->
    <div class="relative">
      <Input
        v-model="searchQuery"
        placeholder="Search messages..."
        class="pl-10"
        @input="onSearchInput"
      />
      <svg
        class="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
      </svg>
      
      <!-- Clear button -->
      <Button
        v-if="searchQuery"
        variant="ghost"
        size="sm"
        @click="clearSearch"
        class="absolute right-2 top-1/2 transform -translate-y-1/2 h-6 w-6 p-0"
      >
        <svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </Button>
    </div>
    
    <!-- Search Filters -->
    <div v-if="searchQuery" class="flex flex-wrap gap-2">
      <Button
        v-for="filter in searchFilters"
        :key="filter.key"
        :variant="activeFilters.includes(filter.key) ? 'default' : 'outline'"
        size="sm"
        @click="toggleFilter(filter.key)"
      >
        {{ filter.label }}
      </Button>
    </div>
    
    <!-- Search Results -->
    <div v-if="searchQuery && searchResults.length > 0" class="space-y-3">
      <div class="flex items-center justify-between">
        <span class="text-sm text-muted-foreground">
          {{ searchResults.length }} result{{ searchResults.length > 1 ? 's' : '' }}
        </span>
        
        <div class="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            @click="previousResult"
            :disabled="currentResultIndex <= 0"
            class="h-6 px-2"
          >
            ↑
          </Button>
          <span class="text-xs text-muted-foreground">
            {{ currentResultIndex + 1 }} / {{ searchResults.length }}
          </span>
          <Button
            variant="ghost"
            size="sm"
            @click="nextResult"
            :disabled="currentResultIndex >= searchResults.length - 1"
            class="h-6 px-2"
          >
            ↓
          </Button>
        </div>
      </div>
      
      <!-- Results List -->
      <div class="space-y-2 max-h-64 overflow-y-auto">
        <div
          v-for="(result, index) in searchResults"
          :key="result.message.id"
          :class="cn(
            'p-3 rounded-lg border cursor-pointer transition-colors',
            index === currentResultIndex
              ? 'bg-primary/10 border-primary'
              : 'hover:bg-muted/50'
          )"
          @click="selectResult(index)"
        >
          <div class="flex items-start gap-3">
            <Avatar
              :fallback="result.message.type === 'user' ? 'U' : 'AI'"
              size="sm"
            />
            
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-1">
                <Badge
                  :variant="result.message.type === 'user' ? 'default' : 'secondary'"
                  class="text-xs"
                >
                  {{ result.message.type === 'user' ? 'User' : 'Assistant' }}
                </Badge>
                <span class="text-xs text-muted-foreground">
                  {{ formatDate(result.message.timestamp) }}
                </span>
              </div>
              
              <div
                class="text-sm text-muted-foreground line-clamp-2"
                v-html="result.highlightedContent"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- No Results -->
    <div
      v-else-if="searchQuery && searchResults.length === 0 && !isSearching"
      class="text-center py-8 text-muted-foreground"
    >
      <p>No messages found</p>
      <p class="text-sm">Try different keywords or adjust your filters</p>
    </div>
    
    <!-- Loading -->
    <div v-if="isSearching" class="space-y-2">
      <div v-for="i in 3" :key="i" class="flex items-center space-x-3 p-3">
        <Skeleton class="h-8 w-8 rounded-full" />
        <div class="space-y-2 flex-1">
          <Skeleton class="h-4 w-3/4" />
          <Skeleton class="h-3 w-1/2" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { ChatMessage } from '@/types'
import { formatDate, cn } from '@/lib/utils'
import { useChatStore } from '@/stores/chat'
import Input from '@/components/ui/Input.vue'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import Avatar from '@/components/ui/Avatar.vue'
import Skeleton from '@/components/ui/Skeleton.vue'

interface SearchResult {
  message: ChatMessage
  highlightedContent: string
  matchScore: number
}

const emit = defineEmits<{
  'message-selected': [message: ChatMessage]
}>()

const chatStore = useChatStore()

const searchQuery = ref('')
const activeFilters = ref<string[]>([])
const searchResults = ref<SearchResult[]>([])
const currentResultIndex = ref(0)
const isSearching = ref(false)
const searchTimeout = ref<NodeJS.Timeout>()

const searchFilters = [
  { key: 'user', label: 'User Messages' },
  { key: 'assistant', label: 'AI Responses' },
  { key: 'with-sources', label: 'With Sources' },
  { key: 'recent', label: 'Recent (7 days)' }
]

const filteredMessages = computed(() => {
  let messages = chatStore.messages
  
  if (activeFilters.value.includes('user')) {
    messages = messages.filter(msg => msg.type === 'user')
  } else if (activeFilters.value.includes('assistant')) {
    messages = messages.filter(msg => msg.type === 'assistant')
  }
  
  if (activeFilters.value.includes('with-sources')) {
    messages = messages.filter(msg => msg.sources && msg.sources.length > 0)
  }
  
  if (activeFilters.value.includes('recent')) {
    const sevenDaysAgo = new Date()
    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7)
    messages = messages.filter(msg => new Date(msg.timestamp) >= sevenDaysAgo)
  }
  
  return messages
})

function onSearchInput() {
  // Debounce search
  if (searchTimeout.value) {
    clearTimeout(searchTimeout.value)
  }
  
  searchTimeout.value = setTimeout(() => {
    performSearch()
  }, 300)
}

function performSearch() {
  if (!searchQuery.value.trim()) {
    searchResults.value = []
    return
  }
  
  isSearching.value = true
  
  try {
    const query = searchQuery.value.toLowerCase()
    const results: SearchResult[] = []
    
    filteredMessages.value.forEach(message => {
      const content = message.content.toLowerCase()
      const matchIndex = content.indexOf(query)
      
      if (matchIndex !== -1) {
        // Calculate match score based on position and length
        const matchScore = 1 - (matchIndex / content.length)
        
        // Create highlighted content
        const highlightedContent = highlightMatches(message.content, searchQuery.value)
        
        results.push({
          message,
          highlightedContent,
          matchScore
        })
      }
    })
    
    // Sort by match score (higher is better)
    results.sort((a, b) => b.matchScore - a.matchScore)
    
    searchResults.value = results
    currentResultIndex.value = 0
  } finally {
    isSearching.value = false
  }
}

function highlightMatches(content: string, query: string): string {
  if (!query) return content
  
  const regex = new RegExp(`(${escapeRegExp(query)})`, 'gi')
  return content.replace(regex, '<mark class="bg-yellow-200 dark:bg-yellow-800">$1</mark>')
}

function escapeRegExp(string: string): string {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function toggleFilter(filterKey: string) {
  const index = activeFilters.value.indexOf(filterKey)
  if (index > -1) {
    activeFilters.value.splice(index, 1)
  } else {
    // Some filters are mutually exclusive
    if (filterKey === 'user' || filterKey === 'assistant') {
      activeFilters.value = activeFilters.value.filter(f => f !== 'user' && f !== 'assistant')
    }
    activeFilters.value.push(filterKey)
  }
  
  // Re-search with new filters
  if (searchQuery.value) {
    performSearch()
  }
}

function clearSearch() {
  searchQuery.value = ''
  searchResults.value = []
  activeFilters.value = []
  currentResultIndex.value = 0
}

function selectResult(index: number) {
  currentResultIndex.value = index
  const result = searchResults.value[index]
  if (result) {
    emit('message-selected', result.message)
  }
}

function nextResult() {
  if (currentResultIndex.value < searchResults.value.length - 1) {
    selectResult(currentResultIndex.value + 1)
  }
}

function previousResult() {
  if (currentResultIndex.value > 0) {
    selectResult(currentResultIndex.value - 1)
  }
}

// Watch for filter changes
watch(activeFilters, () => {
  if (searchQuery.value) {
    performSearch()
  }
}, { deep: true })
</script>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

:deep(mark) {
  @apply bg-yellow-200 dark:bg-yellow-800 px-1 rounded;
}
</style>