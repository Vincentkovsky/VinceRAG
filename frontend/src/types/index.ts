// Document types
export interface Document {
  id: number // Snowflake ID
  name: string
  type: 'pdf' | 'docx' | 'txt' | 'md' | 'pptx' | 'xlsx' | 'csv' | 'rtf' | 'url'
  status: 'processing' | 'completed' | 'failed'
  createdAt: Date
  updatedAt?: Date
  metadata: DocumentMetadata
}

export interface DocumentMetadataBase {
  processingErrors?: string[]
  lastProcessedAt?: Date
  userTags?: string[]
  embeddingModel?: string
}

export interface FileMetadata extends DocumentMetadataBase {
  originalFileName: string
  fileSize: number
  mimeType: string
  chunkCount?: number
}

export interface WebMetadata extends DocumentMetadataBase {
  url: string
  title?: string
  description?: string
  publishedDate?: Date
  scrapedAt: Date
  crawlDepth?: number
  parentUrl?: string
}

export type DocumentMetadata = FileMetadata | WebMetadata

export interface DocumentChunk {
  id: number // Snowflake ID
  documentId: number
  chunkIndex: number
  vectorId: string
  content: string
  startChar: number
  endChar: number
  tokenCount: number
  createdAt: Date
  documentName?: string
  documentType?: string
  similarity?: number
}

// Chat types
export interface ChatMessage {
  id: number // Snowflake ID
  type: 'user' | 'assistant'
  content: string
  sources?: DocumentSource[]
  timestamp: Date
}

export interface ChatSession {
  id: number
  createdAt: Date
}

export interface DocumentSource {
  chunkId: number
  documentId: number
  documentName: string
  documentType: string
  chunk: string
  similarity: number
  chunkIndex: number
  startChar: number
  endChar: number
  tokenCount: number
  url?: string
  mimeType?: string
  author?: string
  publishedDate?: Date
  category?: string
  tags?: string[]
  domain?: string
  language?: string
  contextInfo?: string[]
  highlighted?: string
}

// API types
export interface ApiResponse<T> {
  data: T
  message?: string
  success: boolean
}

export interface ProcessingStatus {
  status: 'processing' | 'completed' | 'failed'
  progress?: number
  message?: string
  updatedAt: string
  metadata?: Record<string, any>
}

// Upload types
export interface UploadProgress {
  fileId: string
  fileName: string
  progress: number
  status: 'uploading' | 'processing' | 'completed' | 'failed'
}

export interface CrawlOptions {
  maxDepth: number
  maxPages: number
  includeSubdomains: boolean
}

// App state types
export interface AppConfig {
  apiBaseUrl: string
  maxFileSize: number
  supportedFileTypes: string[]
  features: {
    webScraping: boolean
    streaming: boolean
    multipleFiles: boolean
  }
}

export interface NotificationMessage {
  id: number
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  message: string
  timestamp: Date
  read: boolean
}