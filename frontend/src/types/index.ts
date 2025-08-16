// Document types
export interface Document {
  id: string // Snowflake ID as string to avoid JavaScript precision issues
  name: string
  type: 'pdf' | 'docx' | 'txt' | 'md' | 'pptx' | 'xlsx' | 'csv' | 'rtf' | 'url'
  status: 'processing' | 'completed' | 'failed'
  created_at: string // ISO string from API
  updated_at?: string // ISO string from API
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
  id: string // Snowflake ID as string
  documentId: string // Snowflake ID as string
  chunkIndex: number
  vectorId: string
  content: string
  startChar: number
  endChar: number
  tokenCount: number
  created_at: string // ISO string from API
  documentName?: string
  documentType?: string
  similarity?: number
}

// Chat types
export interface ChatMessage {
  id: string // Snowflake ID as string
  type: 'user' | 'assistant'
  content: string
  sources?: DocumentSource[]
  timestamp: string // ISO string from API
}

export interface ChatSession {
  id: string // Snowflake ID as string
  created_at: string // ISO string from API
}

export interface DocumentSource {
  chunkId: string // Snowflake ID as string
  documentId: string // Snowflake ID as string
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
  updated_at: string
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
  id: string // Snowflake ID as string
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  message: string
  timestamp: string // ISO string from API
  read: boolean
}

// Auth types
export interface User {
  id: string // Snowflake ID as string
  email: string
  is_active: boolean
  is_superuser: boolean
}

export interface UserCreate {
  email: string
  password: string
}

export interface UserLogin {
  email: string
  password: string
}

export interface Token {
  access_token: string
  token_type: string
}

export interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
}