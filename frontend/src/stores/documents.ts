import { defineStore } from "pinia";
import { ref, computed } from "vue";
import type {
  Document,
  DocumentChunk,
  ProcessingStatus,
  CrawlOptions,
} from "@/types";
import { documentsApi } from "@/api/documents";

export const useDocumentsStore = defineStore("documents", () => {
  // State
  const documents = ref<Document[]>([]);
  const selectedDocument = ref<Document | null>(null);
  const chunks = ref<DocumentChunk[]>([]);
  const isLoading = ref(false);
  const uploadProgress = ref<Map<string, number>>(new Map());
  const processingStatus = ref<Map<string, ProcessingStatus>>(new Map());

  // Getters
  const documentsByStatus = computed(() => {
    return {
      processing: documents.value.filter((doc) => doc.status === "processing"),
      completed: documents.value.filter((doc) => doc.status === "completed"),
      failed: documents.value.filter((doc) => doc.status === "failed"),
    };
  });

  const totalDocuments = computed(() => documents.value.length);
  const completedDocuments = computed(
    () => documentsByStatus.value.completed.length
  );

  // Actions
  async function fetchDocuments() {
    isLoading.value = true;
    try {
      const response = await documentsApi.getDocuments();
      documents.value = response.documents;
    } catch (error) {
      console.error("Failed to fetch documents:", error);
      throw error;
    } finally {
      isLoading.value = false;
    }
  }

  async function uploadDocuments(files: File[]) {
    const uploadPromises = files.map(async (file) => {
      const fileId = `${file.name}-${Date.now()}`;
      uploadProgress.value.set(fileId, 0);

      try {
        const response = await documentsApi.uploadDocument(file, (progress) => {
          uploadProgress.value.set(fileId, progress);
        });

        // Add to documents list
        documents.value.push(response);

        // Start monitoring processing status
        monitorProcessingStatus(response.id);

        return response;
      } catch (error) {
        console.error(`Failed to upload ${file.name}:`, error);
        throw error;
      } finally {
        uploadProgress.value.delete(fileId);
      }
    });

    return Promise.allSettled(uploadPromises);
  }

  async function addUrl(url: string, crawlOptions?: CrawlOptions) {
    try {
      const response = await documentsApi.addUrl(url, crawlOptions);
      documents.value.push(response);
      monitorProcessingStatus(response.id);
      return response;
    } catch (error) {
      console.error("Failed to add URL:", error);
      throw error;
    }
  }

  async function deleteDocument(id: string) {
    try {
      await documentsApi.deleteDocument(id);
      documents.value = documents.value.filter((doc) => doc.id !== id);
      processingStatus.value.delete(id);

      // Clear selected document if it was deleted
      if (selectedDocument.value?.id === id) {
        selectedDocument.value = null;
        chunks.value = [];
      }
    } catch (error) {
      console.error("Failed to delete document:", error);
      throw error;
    }
  }

  async function fetchDocumentChunks(documentId: string) {
    try {
      const response = await documentsApi.getDocumentChunks(documentId);
      chunks.value = response.chunks;
      return response.chunks;
    } catch (error) {
      console.error("Failed to fetch chunks:", error);
      throw error;
    }
  }

  function monitorProcessingStatus(documentId: string) {
    const pollStatus = async () => {
      try {
        const response = await documentsApi.getDocumentStatus(documentId);
        const document = documents.value.find((doc) => doc.id === documentId);

        if (document) {
          document.status = response.status;
          document.updated_at = response.updated_at;

          if (response.metadata) {
            document.metadata = {
              ...document.metadata,
              ...response.metadata,
            };
          }
        }

        processingStatus.value.set(documentId, response);

        // Continue polling if still processing
        if (response.status === "processing") {
          setTimeout(pollStatus, 2000); // Poll every 2 seconds
        }
      } catch (error) {
        console.error("Failed to get processing status:", error);
      }
    };

    pollStatus();
  }

  function selectDocument(document: Document) {
    selectedDocument.value = document;
    fetchDocumentChunks(document.id);
  }

  function clearSelection() {
    selectedDocument.value = null;
    chunks.value = [];
  }

  return {
    // State
    documents,
    selectedDocument,
    chunks,
    isLoading,
    uploadProgress,
    processingStatus,

    // Getters
    documentsByStatus,
    totalDocuments,
    completedDocuments,

    // Actions
    fetchDocuments,
    uploadDocuments,
    addUrl,
    deleteDocument,
    fetchDocumentChunks,
    selectDocument,
    clearSelection,
  };
});
