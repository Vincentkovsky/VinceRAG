<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-3xl font-bold">Document Management</h1>
      <div class="flex items-center space-x-2">
        <Badge variant="secondary">
          {{ documentsStore.totalDocuments }} documents
        </Badge>
        <Badge variant="success">
          {{ documentsStore.completedDocuments }} processed
        </Badge>
      </div>
    </div>

    <!-- Upload Section -->
    <Card class="p-6">
      <h2 class="text-xl font-semibold mb-4">Upload Documents</h2>
      <DocumentUpload />
    </Card>

    <!-- URL Section -->
    <Card class="p-6">
      <h2 class="text-xl font-semibold mb-4">Add Web Content</h2>
      <UrlInput />
    </Card>

    <!-- Documents List -->
    <Card class="p-6">
      <h2 class="text-xl font-semibold mb-4">Your Documents</h2>
      <DocumentList />
    </Card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { useDocumentsStore } from '@/stores/documents'
import { useAuthStore } from '@/stores/auth'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import DocumentUpload from '@/components/documents/DocumentUpload.vue'
import UrlInput from '@/components/documents/UrlInput.vue'
import DocumentList from '@/components/documents/DocumentList.vue'

const documentsStore = useDocumentsStore()
const authStore = useAuthStore()

// Fetch documents when component mounts and user is authenticated
onMounted(() => {
  if (authStore.isAuthenticated) {
    documentsStore.fetchDocuments()
  }
})

// Watch for authentication changes and fetch documents when user logs in
watch(
  () => authStore.isAuthenticated,
  (isAuthenticated) => {
    if (isAuthenticated) {
      documentsStore.fetchDocuments()
    }
  }
)
</script>