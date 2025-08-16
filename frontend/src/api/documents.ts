import apiClient from './client'
import type { Document, DocumentChunk, ProcessingStatus, CrawlOptions, ApiResponse } from '@/types'

export interface DocumentsResponse {
  documents: Document[]
  total: number
  page: number
  pageSize: number
}

export interface DocumentChunksResponse {
  chunks: DocumentChunk[]
  total: number
  page: number
  pageSize: number
}

export interface UploadResponse {
  document: Document
  message: string
}

// For backward compatibility, some endpoints return Document directly
export type DocumentResponse = Document

export const documentsApi = {
  // Get all documents
  async getDocuments(params?: {
    page?: number
    pageSize?: number
    search?: string
    type?: string
    status?: string
  }): Promise<DocumentsResponse> {
    const response = await apiClient.get('/documents', { params })
    return response.data
  },

  // Upload document
  async uploadDocument(
    file: File,
    onProgress?: (progress: number) => void
  ): Promise<Document> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await apiClient.post('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          onProgress(progress)
        }
      },
    })

    return response.data
  },

  // Add URL
  async addUrl(url: string, crawlOptions?: CrawlOptions): Promise<Document> {
    const response = await apiClient.post('/documents/url', {
      url,
      crawl_options: crawlOptions,
    })
    return response.data
  },

  // Crawl website
  async crawlWebsite(url: string, crawlOptions: CrawlOptions): Promise<Document[]> {
    const response = await apiClient.post('/documents/crawl', {
      url,
      ...crawlOptions,
    })
    return response.data
  },

  // Delete document
  async deleteDocument(id: string): Promise<ApiResponse<null>> {
    const response = await apiClient.delete(`/documents/${id}`)
    return response.data
  },

  // Get document status
  async getDocumentStatus(id: string): Promise<ProcessingStatus> {
    const response = await apiClient.get(`/documents/${id}/status`)
    return response.data
  },

  // Get document chunks
  async getDocumentChunks(
    id: string,
    params?: {
      page?: number
      pageSize?: number
    }
  ): Promise<DocumentChunksResponse> {
    const response = await apiClient.get(`/documents/${id}/chunks`, { params })
    return response.data
  },

  // Process document
  async processDocument(id: string): Promise<ApiResponse<null>> {
    const response = await apiClient.post(`/documents/${id}/process`)
    return response.data
  },

  // Get chunk details
  async getChunk(id: string): Promise<DocumentChunk> {
    const response = await apiClient.get(`/chunks/${id}`)
    return response.data
  },

  // Delete chunk
  async deleteChunk(id: string): Promise<ApiResponse<null>> {
    const response = await apiClient.delete(`/chunks/${id}`)
    return response.data
  },
}