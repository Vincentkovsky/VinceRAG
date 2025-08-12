<template>
  <div class="space-y-4">
    <!-- Drag and Drop Area -->
    <div
      ref="dropZone"
      class="border-2 border-dashed rounded-lg p-8 text-center transition-colors"
      :class="{
        'border-primary bg-primary/5': isDragOver,
        'border-muted-foreground/25': !isDragOver
      }"
      @dragover.prevent="handleDragOver"
      @dragleave.prevent="handleDragLeave"
      @drop.prevent="handleDrop"
    >
      <div class="space-y-4">
        <div class="text-4xl">📁</div>
        <div>
          <p class="text-lg font-medium">
            {{ isDragOver ? 'Drop files here' : 'Drag and drop files here' }}
          </p>
          <p class="text-sm text-muted-foreground">
            or click to select files
          </p>
        </div>
        
        <Button @click="triggerFileInput" :disabled="isUploading">
          Select Files
        </Button>
        
        <input
          ref="fileInput"
          type="file"
          multiple
          accept=".pdf,.docx,.txt,.md,.pptx,.xlsx,.csv,.rtf"
          class="hidden"
          @change="handleFileSelect"
        />
      </div>
    </div>

    <!-- File Type Info -->
    <div class="text-sm text-muted-foreground">
      <p class="font-medium mb-1">Supported file types:</p>
      <p>PDF, DOCX, TXT, MD, PPTX, XLSX, CSV, RTF (max 50MB each)</p>
    </div>

    <!-- Upload Progress -->
    <div v-if="uploadFiles.length > 0" class="space-y-3">
      <h3 class="font-medium">Uploading Files</h3>
      <div
        v-for="file in uploadFiles"
        :key="file.id"
        class="flex items-center space-x-3 p-3 border rounded-lg"
      >
        <div class="flex-1">
          <div class="flex items-center justify-between mb-1">
            <span class="text-sm font-medium">{{ file.name }}</span>
            <span class="text-xs text-muted-foreground">
              {{ formatFileSize(file.size) }}
            </span>
          </div>
          <Progress :value="file.progress" class="h-2" />
        </div>
        
        <Badge
          :variant="
            file.status === 'completed' ? 'success' :
            file.status === 'failed' ? 'destructive' :
            'secondary'
          "
        >
          {{ file.status }}
        </Badge>
        
        <Button
          v-if="file.status === 'failed' || file.status === 'completed'"
          variant="ghost"
          size="icon"
          @click="removeUploadFile(file.id)"
        >
          ✕
        </Button>
      </div>
    </div>

    <!-- Validation Errors -->
    <div v-if="validationErrors.length > 0" class="space-y-2">
      <div
        v-for="error in validationErrors"
        :key="error"
        class="text-sm text-destructive bg-destructive/10 p-2 rounded"
      >
        {{ error }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useDocumentsStore } from '@/stores/documents'
import { useAppStore } from '@/stores/app'
import { formatFileSize } from '@/lib/utils'
import Button from '@/components/ui/Button.vue'
import Progress from '@/components/ui/Progress.vue'
import Badge from '@/components/ui/Badge.vue'

interface UploadFile {
  id: string
  name: string
  size: number
  file: File
  progress: number
  status: 'uploading' | 'processing' | 'completed' | 'failed'
}

const documentsStore = useDocumentsStore()
const appStore = useAppStore()

const dropZone = ref<HTMLElement>()
const fileInput = ref<HTMLInputElement>()
const isDragOver = ref(false)
const uploadFiles = ref<UploadFile[]>([])
const validationErrors = ref<string[]>([])

const isUploading = computed(() => 
  uploadFiles.value.some(f => f.status === 'uploading' || f.status === 'processing')
)

const SUPPORTED_TYPES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'text/plain',
  'text/markdown',
  'application/vnd.openxmlformats-officedocument.presentationml.presentation',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  'text/csv',
  'application/rtf'
]

const MAX_FILE_SIZE = 50 * 1024 * 1024 // 50MB

function handleDragOver(event: DragEvent) {
  event.preventDefault()
  isDragOver.value = true
}

function handleDragLeave(event: DragEvent) {
  event.preventDefault()
  isDragOver.value = false
}

function handleDrop(event: DragEvent) {
  event.preventDefault()
  isDragOver.value = false
  
  const files = Array.from(event.dataTransfer?.files || [])
  processFiles(files)
}

function triggerFileInput() {
  fileInput.value?.click()
}

function handleFileSelect(event: Event) {
  const target = event.target as HTMLInputElement
  const files = Array.from(target.files || [])
  processFiles(files)
  
  // Reset input
  target.value = ''
}

function validateFiles(files: File[]): string[] {
  const errors: string[] = []
  
  for (const file of files) {
    // Check file size
    if (file.size > MAX_FILE_SIZE) {
      errors.push(`${file.name}: File size exceeds 50MB limit`)
      continue
    }
    
    // Check file type
    if (!SUPPORTED_TYPES.includes(file.type)) {
      errors.push(`${file.name}: Unsupported file type`)
      continue
    }
  }
  
  return errors
}

async function processFiles(files: File[]) {
  validationErrors.value = []
  
  // Validate files
  const errors = validateFiles(files)
  if (errors.length > 0) {
    validationErrors.value = errors
    return
  }
  
  // Create upload file objects
  const newUploadFiles: UploadFile[] = files.map(file => ({
    id: `${file.name}-${Date.now()}`,
    name: file.name,
    size: file.size,
    file,
    progress: 0,
    status: 'uploading'
  }))
  
  uploadFiles.value.push(...newUploadFiles)
  
  // Upload files
  for (const uploadFile of newUploadFiles) {
    try {
      await documentsStore.uploadDocuments([uploadFile.file])
      
      uploadFile.status = 'completed'
      uploadFile.progress = 100
      
      appStore.addNotification({
        type: 'success',
        title: 'Upload Successful',
        message: `${uploadFile.name} uploaded successfully`
      })
    } catch (error) {
      uploadFile.status = 'failed'
      
      appStore.addNotification({
        type: 'error',
        title: 'Upload Failed',
        message: `Failed to upload ${uploadFile.name}`
      })
    }
  }
}

function removeUploadFile(id: string) {
  uploadFiles.value = uploadFiles.value.filter(f => f.id !== id)
}
</script>