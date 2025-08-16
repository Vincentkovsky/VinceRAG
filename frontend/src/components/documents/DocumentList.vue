<template>
    <div class="space-y-4">
        <!-- Search and Filters -->
        <div class="flex flex-col sm:flex-row gap-4">
            <div class="flex-1">
                <Input v-model="searchQuery" placeholder="Search documents..." class="w-full" />
            </div>

            <div class="flex gap-2">
                <select v-model="selectedType" class="px-3 py-2 border border-input rounded-md bg-background text-sm">
                    <option value="">All Types</option>
                    <option value="pdf">PDF</option>
                    <option value="docx">DOCX</option>
                    <option value="txt">TXT</option>
                    <option value="md">Markdown</option>
                    <option value="pptx">PPTX</option>
                    <option value="xlsx">XLSX</option>
                    <option value="csv">CSV</option>
                    <option value="rtf">RTF</option>
                    <option value="url">Web Page</option>
                </select>

                <select v-model="selectedStatus" class="px-3 py-2 border border-input rounded-md bg-background text-sm">
                    <option value="">All Status</option>
                    <option value="processing">Processing</option>
                    <option value="completed">Completed</option>
                    <option value="failed">Failed</option>
                </select>

                <select v-model="sortBy" class="px-3 py-2 border border-input rounded-md bg-background text-sm">
                    <option value="created_at">Date Added</option>
                    <option value="name">Name</option>
                    <option value="type">Type</option>
                    <option value="status">Status</option>
                </select>
            </div>
        </div>

        <!-- Documents Grid -->
        <div v-if="documentsStore.isLoading" class="text-center py-8">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
            <p class="mt-2 text-muted-foreground">Loading documents...</p>
        </div>

        <div v-else-if="filteredDocuments.length === 0" class="text-center py-8">
            <div class="text-4xl mb-4">📄</div>
            <p class="text-lg font-medium">No documents found</p>
            <p class="text-muted-foreground">
                {{ searchQuery || selectedType || selectedStatus ? 'Try adjusting your filters' : 'Upload your first document to get started' }}
            </p>
        </div>

        <div v-else class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <Card v-for="document in filteredDocuments" :key="document.id"
                class="p-4 hover:shadow-md transition-shadow cursor-pointer" @click="selectDocument(document)">
                <div class="flex items-start justify-between mb-3">
                    <div class="flex items-center space-x-2">
                        <span class="text-2xl">{{ getFileIcon(document.type) }}</span>
                        <div class="flex-1 min-w-0">
                            <h3 class="font-medium truncate" :title="document.name">
                                {{ document.name }}
                            </h3>
                            <p class="text-sm text-muted-foreground">
                                {{ document.type.toUpperCase() }}
                            </p>
                        </div>
                    </div>

                    <div class="flex items-center space-x-2">
                        <Badge :variant="document.status === 'completed' ? 'success' :
                                document.status === 'processing' ? 'secondary' :
                                    'destructive'
                            ">
                            {{ document.status }}
                        </Badge>

                        <Button variant="ghost" size="icon" @click.stop="deleteDocument(document)" class="h-8 w-8">
                            🗑️
                        </Button>
                    </div>
                </div>

                <!-- Processing Progress -->
                <div v-if="document.status === 'processing'" class="mb-3">
                    <div class="flex items-center justify-between text-sm mb-1">
                        <span>Processing...</span>
                        <span>{{ getProcessingProgress(document.id) }}%</span>
                    </div>
                    <Progress :value="getProcessingProgress(document.id)" class="h-2" />
                </div>

                <!-- Document Info -->
                <div class="space-y-2 text-sm text-muted-foreground">
                    <div class="flex justify-between">
                        <span>Added:</span>
                        <span>{{ formatDate(document.created_at) }}</span>
                    </div>

                    <div v-if="'fileSize' in document.document_metadata" class="flex justify-between">
                        <span>Size:</span>
                        <span>{{ formatFileSize(document.document_metadata.fileSize) }}</span>
                    </div>

                    <div v-if="'url' in document.document_metadata" class="flex justify-between">
                        <span>URL:</span>
                        <span class="truncate max-w-32" :title="document.document_metadata.url">
                            {{ document.document_metadata.url }}
                        </span>
                    </div>

                    <div v-if="'chunkCount' in document.document_metadata && document.document_metadata.chunkCount"
                        class="flex justify-between">
                        <span>Chunks:</span>
                        <span>{{ document.document_metadata.chunkCount }}</span>
                    </div>
                </div>
            </Card>
        </div>

        <!-- Delete Confirmation Dialog -->
        <div v-if="documentToDelete" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
            @click="cancelDelete">
            <Card class="p-6 max-w-md mx-4" @click.stop>
                <h3 class="text-lg font-semibold mb-2">Delete Document</h3>
                <p class="text-muted-foreground mb-4">
                    Are you sure you want to delete "{{ documentToDelete.name }}"? This action cannot be undone.
                </p>

                <div class="flex justify-end space-x-2">
                    <Button variant="outline" @click="cancelDelete">
                        Cancel
                    </Button>
                    <Button variant="destructive" @click="confirmDelete">
                        Delete
                    </Button>
                </div>
            </Card>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useDocumentsStore } from '@/stores/documents'
import { useAppStore } from '@/stores/app'
import { formatFileSize, formatDate, getFileIcon } from '@/lib/utils'
import type { Document } from '@/types'
import Card from '@/components/ui/Card.vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Badge from '@/components/ui/Badge.vue'
import Progress from '@/components/ui/Progress.vue'

const documentsStore = useDocumentsStore()
const appStore = useAppStore()

const searchQuery = ref('')
const selectedType = ref('')
const selectedStatus = ref('')
const sortBy = ref('created_at')
const documentToDelete = ref<Document | null>(null)

const filteredDocuments = computed(() => {
    let filtered = [...documentsStore.documents]

    // Apply search filter
    if (searchQuery.value) {
        const query = searchQuery.value.toLowerCase()
        filtered = filtered.filter(doc =>
            doc.name.toLowerCase().includes(query) ||
            doc.type.toLowerCase().includes(query)
        )
    }

    // Apply type filter
    if (selectedType.value) {
        filtered = filtered.filter(doc => doc.type === selectedType.value)
    }

    // Apply status filter
    if (selectedStatus.value) {
        filtered = filtered.filter(doc => doc.status === selectedStatus.value)
    }

    // Apply sorting
    filtered.sort((a, b) => {
        switch (sortBy.value) {
            case 'name':
                return a.name.localeCompare(b.name)
            case 'type':
                return a.type.localeCompare(b.type)
            case 'status':
                return a.status.localeCompare(b.status)
            case 'created_at':
            default:
                return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        }
    })

    return filtered
})

function selectDocument(document: Document) {
    documentsStore.selectDocument(document)
    // Could navigate to document detail view or show chunks
}

function deleteDocument(document: Document) {
    documentToDelete.value = document
}

function cancelDelete() {
    documentToDelete.value = null
}

async function confirmDelete() {
    if (!documentToDelete.value) return

    try {
        await documentsStore.deleteDocument(documentToDelete.value.id)

        appStore.addNotification({
            type: 'success',
            title: 'Document Deleted',
            message: `${documentToDelete.value.name} has been deleted`
        })
    } catch (error) {
        appStore.addNotification({
            type: 'error',
            title: 'Delete Failed',
            message: 'Failed to delete document'
        })
    } finally {
        documentToDelete.value = null
    }
}

function getProcessingProgress(documentId: string): number {
    const status = documentsStore.processingStatus.get(documentId)
    return status?.progress || 0
}
</script>