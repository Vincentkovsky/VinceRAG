# Design Document

## Overview

This document outlines the technical design for a professional RAG (Retrieval-Augmented Generation) system built with LangChain and Vue.js. The system follows a microservices architecture with clear separation between frontend, backend API, document processing, and vector storage components.

## Architecture

### High-Level Architecture

```mermaid
graph TB
    subgraph "Frontend Layer"
        VUE[Vue.js Application]
        UI[User Interface Components]
    end
    
    subgraph "API Layer"
        API[FastAPI Backend]
        AUTH[Authentication Service]
        UPLOAD[File Upload Service]
        WEB[Web Scraping Service]
    end
    
    subgraph "Processing Layer"
        DOC[Document Processor]
        EMBED[Embedding Service]
        CHUNK[Text Chunking Service]
    end
    
    subgraph "Storage Layer"
        VDB[(Vector Database)]
        RDB[(Relational Database)]
        FS[(File Storage)]
    end
    
    subgraph "AI Layer"
        LLM[LangChain LLM]
        EMB[Embedding Model]
    end
    
    VUE --> API
    API --> DOC
    API --> AUTH
    API --> UPLOAD
    API --> WEB
    DOC --> EMBED
    DOC --> CHUNK
    EMBED --> EMB
    EMBED --> VDB
    API --> VDB
    API --> RDB
    UPLOAD --> FS
    API --> LLM
```

### Technology Stack

**Frontend:**
- Vue.js 3 with Composition API
- TypeScript for type safety
- Pinia for state management
- shadcn/ui for component library
- Tailwind CSS (as shadcn/ui dependency)
- Axios for HTTP requests with interceptors
- Vue Router for navigation
- PWA capabilities with Workbox
- Socket.io-client for real-time updates

**Backend:**
- Python with FastAPI framework
- LangChain for RAG orchestration
- Pydantic for data validation
- SQLAlchemy for database ORM
- Celery with Redis for background tasks
- Redis for caching and session storage
- Gunicorn with Uvicorn workers for production

**Infrastructure:**
- PostgreSQL for relational data
- Redis for caching and message queuing
- Nginx as reverse proxy and load balancer
- Docker containers for deployment
- Kubernetes for orchestration (optional)

**Vector Database:**
- Chroma (primary) with Pinecone fallback
- Support for similarity search and metadata filtering
- Connection pooling and failover mechanisms

**Document Processing:**
- PyPDF2/pdfplumber for PDF processing
- python-docx for Word documents
- openpyxl for Excel files
- Playwright for dynamic web content scraping
- BeautifulSoup for static HTML parsing
- python-magic for file type detection

**Embedding Models:**
- OpenAI embeddings (text-embedding-ada-002)
- Support for local models (sentence-transformers)
- Hugging Face transformers for multilingual support

**Monitoring & Observability:**
- Prometheus for metrics collection
- Grafana for visualization
- Sentry for error tracking
- Structured logging with JSON format
- OpenTelemetry for distributed tracing

**Security:**
- JWT for authentication
- bcrypt for password hashing
- python-multipart for file upload security
- ClamAV for malware scanning
- Rate limiting with slowapi

## Components and Interfaces

### Frontend Components

#### shadcn/ui Component Usage

The frontend will leverage shadcn/ui components for consistent design and better developer experience:

**Core Components:**
- `Card` - Document list items, message bubbles, settings panels
- `Button` - All interactive actions (upload, delete, send, etc.)
- `Input` - Text inputs for URLs, search, and message input
- `Badge` - Status indicators (processing, completed, failed)
- `Progress` - Upload and processing progress bars
- `Dialog` - Confirmation modals and settings dialogs
- `ScrollArea` - Chat message container and document lists
- `Avatar` - User and assistant icons in chat
- `Skeleton` - Loading states for messages and documents
- `Collapsible` - Expandable source citations
- `Tabs` - Navigation between document management and chat
- `Alert` - Error messages and notifications
- `Separator` - Visual dividers in UI sections

### Frontend State Management with Pinia

```typescript
// stores/documents.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Document, DocumentChunk, ProcessingStatus } from '@/types'
import { documentsApi } from '@/api/documents'

export const useDocumentsStore = defineStore('documents', () => {
  // State
  const documents = ref<Document[]>([])
  const selectedDocument = ref<Document | null>(null)
  const chunks = ref<DocumentChunk[]>([])
  const isLoading = ref(false)
  const uploadProgress = ref<Map<string, number>>(new Map())
  const processingStatus = ref<Map<number, ProcessingStatus>>(new Map())
  
  // Getters
  const documentsByStatus = computed(() => {
    return {
      processing: documents.value.filter(doc => doc.status === 'processing'),
      completed: documents.value.filter(doc => doc.status === 'completed'),
      failed: documents.value.filter(doc => doc.status === 'failed')
    }
  })
  
  const totalDocuments = computed(() => documents.value.length)
  const completedDocuments = computed(() => documentsByStatus.value.completed.length)
  
  // Actions
  async function fetchDocuments() {
    isLoading.value = true
    try {
      const response = await documentsApi.getDocuments()
      documents.value = response.documents
    } catch (error) {
      console.error('Failed to fetch documents:', error)
      throw error
    } finally {
      isLoading.value = false
    }
  }
  
  async function uploadDocuments(files: File[]) {
    const uploadPromises = files.map(async (file) => {
      const fileId = `${file.name}-${Date.now()}`
      uploadProgress.value.set(fileId, 0)
      
      try {
        const response = await documentsApi.uploadDocument(file, (progress) => {
          uploadProgress.value.set(fileId, progress)
        })
        
        // Add to documents list
        documents.value.push(response.document)
        
        // Start monitoring processing status
        monitorProcessingStatus(response.document.id)
        
        return response.document
      } catch (error) {
        console.error(`Failed to upload ${file.name}:`, error)
        throw error
      } finally {
        uploadProgress.value.delete(fileId)
      }
    })
    
    return Promise.allSettled(uploadPromises)
  }
  
  async function addUrl(url: string, crawlOptions?: CrawlOptions) {
    try {
      const response = await documentsApi.addUrl(url, crawlOptions)
      documents.value.push(response.document)
      monitorProcessingStatus(response.document.id)
      return response.document
    } catch (error) {
      console.error('Failed to add URL:', error)
      throw error
    }
  }
  
  async function deleteDocument(id: number) {
    try {
      await documentsApi.deleteDocument(id)
      documents.value = documents.value.filter(doc => doc.id !== id)
      processingStatus.value.delete(id)
      
      // Clear selected document if it was deleted
      if (selectedDocument.value?.id === id) {
        selectedDocument.value = null
        chunks.value = []
      }
    } catch (error) {
      console.error('Failed to delete document:', error)
      throw error
    }
  }
  
  async function fetchDocumentChunks(documentId: number) {
    try {
      const response = await documentsApi.getDocumentChunks(documentId)
      chunks.value = response.chunks
      return response.chunks
    } catch (error) {
      console.error('Failed to fetch chunks:', error)
      throw error
    }
  }
  
  function monitorProcessingStatus(documentId: number) {
    const pollStatus = async () => {
      try {
        const response = await documentsApi.getDocumentStatus(documentId)
        const document = documents.value.find(doc => doc.id === documentId)
        
        if (document) {
          document.status = response.status
          document.updatedAt = new Date(response.updatedAt)
          
          if (response.metadata) {
            document.metadata = { ...document.metadata, ...response.metadata }
          }
        }
        
        processingStatus.value.set(documentId, response)
        
        // Continue polling if still processing
        if (response.status === 'processing') {
          setTimeout(pollStatus, 2000) // Poll every 2 seconds
        }
      } catch (error) {
        console.error('Failed to get processing status:', error)
      }
    }
    
    pollStatus()
  }
  
  function selectDocument(document: Document) {
    selectedDocument.value = document
    fetchDocumentChunks(document.id)
  }
  
  function clearSelection() {
    selectedDocument.value = null
    chunks.value = []
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
    clearSelection
  }
})

// stores/chat.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { ChatMessage, ChatSession } from '@/types'
import { chatApi } from '@/api/chat'

export const useChatStore = defineStore('chat', () => {
  // State
  const messages = ref<ChatMessage[]>([])
  const currentSession = ref<ChatSession | null>(null)
  const sessions = ref<ChatSession[]>([])
  const isLoading = ref(false)
  const isStreaming = ref(false)
  const streamingMessage = ref('')
  
  // Getters
  const lastMessage = computed(() => 
    messages.value[messages.value.length - 1]
  )
  
  const hasMessages = computed(() => messages.value.length > 0)
  
  // Actions
  async function sendMessage(content: string) {
    const userMessage: ChatMessage = {
      id: Date.now(), // Temporary ID
      type: 'user',
      content,
      timestamp: new Date()
    }
    
    messages.value.push(userMessage)
    isLoading.value = true
    
    try {
      const response = await chatApi.sendMessage(content, currentSession.value?.id)
      
      // Update session if new
      if (response.sessionId && !currentSession.value) {
        currentSession.value = { id: response.sessionId, createdAt: new Date() }
      }
      
      const assistantMessage: ChatMessage = {
        id: response.messageId,
        type: 'assistant',
        content: response.answer,
        sources: response.sources,
        timestamp: new Date()
      }
      
      messages.value.push(assistantMessage)
    } catch (error) {
      console.error('Failed to send message:', error)
      throw error
    } finally {
      isLoading.value = false
    }
  }
  
  async function sendStreamingMessage(content: string) {
    const userMessage: ChatMessage = {
      id: Date.now(),
      type: 'user',
      content,
      timestamp: new Date()
    }
    
    messages.value.push(userMessage)
    isStreaming.value = true
    streamingMessage.value = ''
    
    try {
      const stream = await chatApi.sendStreamingMessage(content, currentSession.value?.id)
      
      for await (const chunk of stream) {
        streamingMessage.value += chunk
      }
      
      const assistantMessage: ChatMessage = {
        id: Date.now(),
        type: 'assistant',
        content: streamingMessage.value,
        timestamp: new Date()
      }
      
      messages.value.push(assistantMessage)
    } catch (error) {
      console.error('Failed to send streaming message:', error)
      throw error
    } finally {
      isStreaming.value = false
      streamingMessage.value = ''
    }
  }
  
  async function loadChatHistory() {
    try {
      const response = await chatApi.getChatHistory()
      messages.value = response.messages
      currentSession.value = response.session
    } catch (error) {
      console.error('Failed to load chat history:', error)
    }
  }
  
  async function clearChatHistory() {
    try {
      await chatApi.clearChatHistory()
      messages.value = []
      currentSession.value = null
    } catch (error) {
      console.error('Failed to clear chat history:', error)
      throw error
    }
  }
  
  function startNewSession() {
    messages.value = []
    currentSession.value = null
  }
  
  return {
    // State
    messages,
    currentSession,
    sessions,
    isLoading,
    isStreaming,
    streamingMessage,
    
    // Getters
    lastMessage,
    hasMessages,
    
    // Actions
    sendMessage,
    sendStreamingMessage,
    loadChatHistory,
    clearChatHistory,
    startNewSession
  }
})

// stores/app.ts - Global application state
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { AppConfig, NotificationMessage } from '@/types'

export const useAppStore = defineStore('app', () => {
  // State
  const config = ref<AppConfig | null>(null)
  const notifications = ref<NotificationMessage[]>([])
  const isOnline = ref(navigator.onLine)
  const theme = ref<'light' | 'dark'>('light')
  const sidebarCollapsed = ref(false)
  
  // Getters
  const hasNotifications = computed(() => notifications.value.length > 0)
  const unreadNotifications = computed(() => 
    notifications.value.filter(n => !n.read)
  )
  
  // Actions
  function addNotification(notification: Omit<NotificationMessage, 'id' | 'timestamp'>) {
    const newNotification: NotificationMessage = {
      ...notification,
      id: Date.now(),
      timestamp: new Date(),
      read: false
    }
    
    notifications.value.unshift(newNotification)
    
    // Auto-remove after 5 seconds for success messages
    if (notification.type === 'success') {
      setTimeout(() => {
        removeNotification(newNotification.id)
      }, 5000)
    }
  }
  
  function removeNotification(id: number) {
    notifications.value = notifications.value.filter(n => n.id !== id)
  }
  
  function markNotificationAsRead(id: number) {
    const notification = notifications.value.find(n => n.id === id)
    if (notification) {
      notification.read = true
    }
  }
  
  function toggleTheme() {
    theme.value = theme.value === 'light' ? 'dark' : 'light'
    localStorage.setItem('theme', theme.value)
  }
  
  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
    localStorage.setItem('sidebarCollapsed', String(sidebarCollapsed.value))
  }
  
  function setOnlineStatus(online: boolean) {
    isOnline.value = online
  }
  
  // Initialize from localStorage
  function initializeFromStorage() {
    const savedTheme = localStorage.getItem('theme') as 'light' | 'dark'
    if (savedTheme) {
      theme.value = savedTheme
    }
    
    const savedSidebarState = localStorage.getItem('sidebarCollapsed')
    if (savedSidebarState) {
      sidebarCollapsed.value = savedSidebarState === 'true'
    }
  }
  
  return {
    // State
    config,
    notifications,
    isOnline,
    theme,
    sidebarCollapsed,
    
    // Getters
    hasNotifications,
    unreadNotifications,
    
    // Actions
    addNotification,
    removeNotification,
    markNotificationAsRead,
    toggleTheme,
    toggleSidebar,
    setOnlineStatus,
    initializeFromStorage
  }
})
```

#### 1. Document Management Component
```typescript
// Using shadcn/ui components: Card, Button, Input, Badge, Progress, Dialog
interface DocumentManagerProps {
  documents: Document[]
  onUpload: (files: File[]) => Promise<void>
  onAddUrl: (url: string, crawlSubpages?: boolean) => Promise<void>
  onDelete: (id: number) => Promise<void>  // Use Snowflake ID
  onViewChunks?: (documentId: number) => Promise<void>  // View document chunks
}

interface ChunkViewerProps {
  documentId: number
  chunks: DocumentChunk[]
  onDeleteChunk: (chunkId: number) => Promise<void>
  onEditChunk?: (chunkId: number, content: string) => Promise<void>
  isLoading: boolean
}

interface ChunkResult {
  chunk: DocumentChunk
  similarity: number      // Similarity score from vector search
  highlighted: string     // Content with search terms highlighted
}

interface CrawlOptions {
  maxDepth: number      // Maximum crawl depth (default: 2)
  maxPages: number      // Maximum pages to crawl (default: 10)
  includeSubdomains: boolean  // Whether to include subdomains
}

interface DocumentMetadataBase {
  processingErrors?: string[];
  lastProcessedAt?: Date;
  userTags?: string[];
  embeddingModel?: string;
}

interface FileMetadata extends DocumentMetadataBase {
  originalFileName: string;
  fileSize: number;
  mimeType: string;
  chunkCount?: number;
}

interface WebMetadata extends DocumentMetadataBase {
  url: string;
  title?: string;
  description?: string;
  publishedDate?: Date;
  scrapedAt: Date;
  crawlDepth?: number;
  parentUrl?: string;
}

type DocumentMetadata = FileMetadata | WebMetadata;
  

interface Document {
  id: number  // Snowflake ID (64-bit integer)
  name: string
  type: 'pdf' | 'docx' | 'txt' | 'md' | 'pptx' | 'xlsx' | 'csv' | 'rtf' | 'url'
  status: 'processing' | 'completed' | 'failed'
  createdAt: Date
  updatedAt?: Date
  metadata: DocumentMetadata
}

interface DocumentChunk {
  id: number              // Snowflake ID (same as vector_id)
  documentId: number      // References Document.id
  chunkIndex: number      // Position within document (0-based)
  vectorId: string        // Reference to vector database entry
  content: string         // Full text content of the chunk
  startChar: number       // Start character position in original document
  endChar: number         // End character position in original document
  tokenCount: number      // Number of tokens in this chunk
  createdAt: Date         // When chunk was created
  
  // Computed properties (from parent document)
  documentName?: string   // Document name for display
  documentType?: string   // Document type for filtering
  similarity?: number     // Similarity score (computed during retrieval)
}

// Component structure with shadcn/ui
// - Card for document list items
// - Button for upload/delete actions
// - Input for URL entry
// - Badge for status indicators
// - Progress for upload/processing progress
// - Dialog for confirmation modals
```

#### 2. Chat Interface Component
```typescript
// Using shadcn/ui components: ScrollArea, Avatar, Button, Input, Skeleton, Collapsible
interface ChatInterfaceProps {
  messages: ChatMessage[]
  onSendMessage: (message: string) => Promise<void>
  isLoading: boolean
}

interface ChatMessage {
  id: number  // Snowflake ID
  type: 'user' | 'assistant'
  content: string
  sources?: DocumentSource[]
  timestamp: Date
}

interface DocumentSource {
  // Core chunk information
  chunkId: number         // DocumentChunk.id
  documentId: number      // DocumentChunk.documentId
  documentName: string    // Document.name with icon
  documentType: 'pdf' | 'docx' | 'txt' | 'md' | 'pptx' | 'xlsx' | 'csv' | 'rtf' | 'url'
  
  // Content and relevance
  chunk: string           // DocumentChunk.content (truncated for display)
  similarity: number      // Similarity score from vector search
  chunkIndex: number      // DocumentChunk.chunkIndex
  
  // Position information
  startChar: number       // DocumentChunk.startChar
  endChar: number         // DocumentChunk.endChar
  tokenCount: number      // DocumentChunk.tokenCount
  
  // Document metadata (from parent document)
  url?: string           // Document.url (for web pages)
  mimeType?: string      // Document.metadata.mimeType
  author?: string        // Document.metadata.author
  publishedDate?: Date   // Document.metadata.publishedDate
  category?: string      // Document.metadata.category
  tags?: string[]        // Document.metadata.tags
  domain?: string        // Document.metadata.domain
  language?: string      // Document.metadata.language
  
  // Display helpers
  contextInfo?: string[] // Formatted context information
  highlighted?: string   // Content with search terms highlighted
}

// Component structure with shadcn/ui
// - ScrollArea for message container
// - Avatar for user/assistant icons
// - Button for send action
// - Input for message input
// - Skeleton for loading states
// - Collapsible for source citations
// - Card for message bubbles
```

### Backend API Endpoints

#### Document Management API
```python
# Document upload and management
POST /api/documents/upload
POST /api/documents/url          # Single page scraping
POST /api/documents/crawl        # Multi-page crawling
GET /api/documents
DELETE /api/documents/{document_id}  # document_id is Snowflake ID (int64)
GET /api/documents/{document_id}/status

# Content processing
POST /api/documents/{document_id}/process  # document_id is Snowflake ID (int64)
GET /api/documents/{document_id}/chunks    # Get chunks for a document
GET /api/chunks/{chunk_id}                 # Get specific chunk details
DELETE /api/chunks/{chunk_id}              # Delete specific chunk
```

#### Chat API
```python
# Q&A functionality
POST /api/chat/query          # Standard query with full response
POST /api/chat/query/stream   # Streaming query with SSE
GET /api/chat/history
DELETE /api/chat/history
GET /api/chat/sessions        # Get chat sessions

# Example API Responses with Snowflake IDs

GET /api/documents
{
  "documents": [
    {
      "id": 1234567890123456789,  // Snowflake ID
      "name": "research_paper.pdf",
      "type": "pdf",
      "status": "completed",
      "createdAt": "2024-01-15T10:30:00Z",
      "metadata": {
        "originalFileName": "research_paper.pdf",
        "fileSize": 2048576,
        "mimeType": "application/pdf",
        "chunkCount": 45,
        "processingTime": 12.5,
        "embeddingModel": "text-embedding-ada-002"
      }
    }
  ]
}

GET /api/documents/1234567890123456789/chunks
{
  "chunks": [
    {
      "id": 9876543210987654321,           // Chunk Snowflake ID
      "documentId": 1234567890123456789,   // Parent document ID
      "chunkIndex": 0,                     // First chunk
      "vectorId": "9876543210987654321",   // Same as ID for vector DB
      "content": "This research paper explores the applications of artificial intelligence...",
      "startChar": 0,
      "endChar": 1000,
      "tokenCount": 200,
      "createdAt": "2024-01-15T10:30:00Z",
      "documentName": "research_paper.pdf",
      "documentType": "pdf"
    },
    {
      "id": 9876543210987654322,
      "documentId": 1234567890123456789,
      "chunkIndex": 1,
      "vectorId": "9876543210987654322",
      "content": "The methodology section describes our approach to data collection...",
      "startChar": 1000,
      "endChar": 2000,
      "tokenCount": 195,
      "createdAt": "2024-01-15T10:30:00Z",
      "documentName": "research_paper.pdf",
      "documentType": "pdf"
    }
  ],
  "total": 45,
  "page": 1,
  "pageSize": 20
}

POST /api/chat/query
{
  "query": "What is artificial intelligence?",
  "answer": "Artificial intelligence is a field of computer science...",
  "sources": [
    {
      "chunkId": 9876543210987654321,
      "documentId": 1234567890123456789,
      "documentName": "📄 research_paper.pdf",
      "documentType": "pdf",
      "chunk": "This research paper explores the applications of artificial intelligence in modern computing systems...",
      "similarity": 0.89,
      "chunkIndex": 0,
      "startChar": 0,
      "endChar": 1000,
      "tokenCount": 200,
      "mimeType": "application/pdf",
      "contextInfo": ["Page 1", "Introduction Section"],
      "highlighted": "This research paper explores the applications of <mark>artificial intelligence</mark> in modern computing systems..."
    }
  ],
  "confidence": 0.85
}
```

#### Configuration API
```python
# System configuration
GET /api/config
PUT /api/config
GET /api/health
GET /api/metrics
```

### Core Services

#### 0. Snowflake ID Generator Service
```python
import time
import threading
from typing import Optional

class SnowflakeIDGenerator:
    """
    Snowflake ID generator for distributed unique ID generation
    
    Snowflake ID structure (64 bits):
    - 1 bit: unused (always 0)
    - 41 bits: timestamp (milliseconds since epoch)
    - 10 bits: machine/worker ID
    - 12 bits: sequence number
    """
    
    def __init__(self, worker_id: int = 1, datacenter_id: int = 1):
        # Validate worker and datacenter IDs
        if worker_id > 31 or worker_id < 0:
            raise ValueError("Worker ID must be between 0 and 31")
        if datacenter_id > 31 or datacenter_id < 0:
            raise ValueError("Datacenter ID must be between 0 and 31")
            
        self.worker_id = worker_id
        self.datacenter_id = datacenter_id
        self.sequence = 0
        self.last_timestamp = -1
        self.lock = threading.Lock()
        
        # Epoch timestamp (2024-01-01 00:00:00 UTC)
        self.epoch = 1704067200000
        
        # Bit shifts
        self.worker_id_bits = 5
        self.datacenter_id_bits = 5
        self.sequence_bits = 12
        
        # Max values
        self.max_worker_id = (1 << self.worker_id_bits) - 1
        self.max_datacenter_id = (1 << self.datacenter_id_bits) - 1
        self.max_sequence = (1 << self.sequence_bits) - 1
        
        # Bit shifts for ID generation
        self.worker_id_shift = self.sequence_bits
        self.datacenter_id_shift = self.sequence_bits + self.worker_id_bits
        self.timestamp_shift = (self.sequence_bits + self.worker_id_bits + 
                               self.datacenter_id_bits)
    
    def generate_id(self) -> int:
        """Generate a unique Snowflake ID"""
        with self.lock:
            timestamp = self._current_timestamp()
            
            if timestamp < self.last_timestamp:
                raise Exception("Clock moved backwards. Refusing to generate ID")
            
            if timestamp == self.last_timestamp:
                self.sequence = (self.sequence + 1) & self.max_sequence
                if self.sequence == 0:
                    # Sequence exhausted, wait for next millisecond
                    timestamp = self._wait_next_timestamp(self.last_timestamp)
            else:
                self.sequence = 0
            
            self.last_timestamp = timestamp
            
            # Generate the ID
            snowflake_id = (
                ((timestamp - self.epoch) << self.timestamp_shift) |
                (self.datacenter_id << self.datacenter_id_shift) |
                (self.worker_id << self.worker_id_shift) |
                self.sequence
            )
            
            return snowflake_id
    
    def _current_timestamp(self) -> int:
        """Get current timestamp in milliseconds"""
        return int(time.time() * 1000)
    
    def _wait_next_timestamp(self, last_timestamp: int) -> int:
        """Wait until next millisecond"""
        timestamp = self._current_timestamp()
        while timestamp <= last_timestamp:
            timestamp = self._current_timestamp()
        return timestamp
    
    def parse_id(self, snowflake_id: int) -> dict:
        """Parse a Snowflake ID into its components"""
        timestamp = ((snowflake_id >> self.timestamp_shift) + self.epoch)
        datacenter_id = ((snowflake_id >> self.datacenter_id_shift) & 
                        self.max_datacenter_id)
        worker_id = (snowflake_id >> self.worker_id_shift) & self.max_worker_id
        sequence = snowflake_id & self.max_sequence
        
        return {
            'timestamp': timestamp,
            'datacenter_id': datacenter_id,
            'worker_id': worker_id,
            'sequence': sequence,
            'datetime': time.strftime('%Y-%m-%d %H:%M:%S', 
                                    time.localtime(timestamp / 1000))
        }

# Global instance
snowflake_generator = SnowflakeIDGenerator()

def generate_document_id() -> int:
    """Generate a unique document ID using Snowflake algorithm"""
    return snowflake_generator.generate_id()
```

#### 1. Document Processing Service
```python
class DocumentProcessor:
    def __init__(self, embedding_service: EmbeddingService):
        self.embedding_service = embedding_service
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
    
    async def process_document(self, document_id: int, document_data: dict) -> ProcessingResult:
        # Extract text based on document type
        text = await self.extract_text(document)
        
        # Split into chunks
        chunks = self.text_splitter.split_text(text)
        
        # Generate embeddings
        embeddings = await self.embedding_service.embed_documents(chunks)
        
        # Store in vector database with Snowflake ID
        await self.store_embeddings(document_id, chunks, embeddings)
        
        return ProcessingResult(success=True, chunks_count=len(chunks))
```

#### 2. Web Scraping Service
```python
import asyncio
import aiohttp
from urllib.robotparser import RobotFileParser
from playwright.async_api import async_playwright
from ratelimit import limits, sleep_and_retry
import time

class WebScrapingService:
    def __init__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'User-Agent': 'RAG-System-Bot/1.0'}
        )
        self.max_depth = 2  # Maximum crawl depth
        self.max_pages = 10  # Maximum pages per domain
        self.visited_urls = set()
        self.robots_cache = {}  # Cache robots.txt files
        self.rate_limits = {}  # Per-domain rate limiting
        self.playwright = None
        
    async def initialize_playwright(self):
        """Initialize Playwright for dynamic content"""
        if not self.playwright:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=True)
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.playwright:
            await self.browser.close()
            await self.playwright.stop()
        await self.session.close()
    
    @sleep_and_retry
    @limits(calls=10, period=60)  # 10 requests per minute per domain
    async def scrape_url(self, url: str, crawl_options: CrawlOptions = None) -> List[ScrapedContent]:
        """
        Scrape a URL with comprehensive options and safety checks
        """
        if not crawl_options:
            crawl_options = CrawlOptions(maxDepth=1, maxPages=1, includeSubdomains=False)
            
        # Check robots.txt compliance
        if not await self.is_crawl_allowed(url):
            raise SecurityError(f"Crawling not allowed by robots.txt for {url}")
        
        # Apply domain-specific rate limiting
        await self.apply_rate_limit(url)
        
        if crawl_options.maxDepth > 1 and crawl_options.maxPages > 1:
            return await self.crawl_website(url, crawl_options)
        else:
            content = await self.scrape_single_page(url)
            return [content]
    
    async def is_crawl_allowed(self, url: str) -> bool:
        """Check if crawling is allowed by robots.txt"""
        from urllib.parse import urljoin, urlparse
        
        domain = urlparse(url).netloc
        if domain not in self.robots_cache:
            robots_url = urljoin(f"https://{domain}", "/robots.txt")
            try:
                async with self.session.get(robots_url) as response:
                    if response.status == 200:
                        robots_txt = await response.text()
                        rp = RobotFileParser()
                        rp.set_url(robots_url)
                        rp.read_robots_txt(robots_txt)
                        self.robots_cache[domain] = rp
                    else:
                        self.robots_cache[domain] = None
            except Exception:
                self.robots_cache[domain] = None
        
        robots = self.robots_cache.get(domain)
        if robots:
            return robots.can_fetch('RAG-System-Bot', url)
        return True  # Allow if no robots.txt or error
    
    async def apply_rate_limit(self, url: str):
        """Apply per-domain rate limiting"""
        domain = urlparse(url).netloc
        current_time = time.time()
        
        if domain in self.rate_limits:
            last_request = self.rate_limits[domain]
            time_diff = current_time - last_request
            if time_diff < 1.0:  # Minimum 1 second between requests
                await asyncio.sleep(1.0 - time_diff)
        
        self.rate_limits[domain] = current_time
    
    async def scrape_single_page(self, url: str, use_playwright: bool = False) -> ScrapedContent:
        # Validate URL security
        if not self.is_safe_url(url):
            raise SecurityError("Potentially malicious URL detected")
        
        try:
            if use_playwright:
                # Use Playwright for dynamic content
                await self.initialize_playwright()
                page = await self.browser.new_page()
                await page.goto(url, wait_until='networkidle')
                html = await page.content()
                await page.close()
            else:
                # Use aiohttp for static content
                async with self.session.get(url) as response:
                    if response.status != 200:
                        raise Exception(f"HTTP {response.status}: {response.reason}")
                    html = await response.text()
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract title and content
            title = soup.find('title').text.strip() if soup.find('title') else url
            content = self.extract_main_content(soup)
            
            # Validate content quality
            if len(content.strip()) < 100:
                logger.warning(f"Low content quality for {url}: {len(content)} characters")
            
            return ScrapedContent(
                url=url,
                title=title,
                content=content,
                metadata={
                    'url': url,
                    'title': title,
                    'scrapedAt': datetime.utcnow(),
                    'domain': urlparse(url).netloc,
                    'textLength': len(content),
                    'language': self.detect_language(content),
                    'description': self.extract_meta_description(soup),
                    'author': self.extract_author(soup),
                    'publishedDate': self.extract_published_date(soup),
                    'keywords': self.extract_keywords(soup),
                    'contentType': 'dynamic' if use_playwright else 'static',
                    'httpStatus': 200,
                    'lastModified': self.extract_last_modified(soup)
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to scrape {url}: {str(e)}")
            # Try with Playwright if static scraping failed
            if not use_playwright:
                logger.info(f"Retrying {url} with Playwright")
                return await self.scrape_single_page(url, use_playwright=True)
            raise ScrapingError(f"Failed to scrape {url}: {str(e)}")
    
    def is_safe_url(self, url: str) -> bool:
        """Enhanced URL security validation"""
        try:
            parsed = urlparse(url)
            
            # Check protocol
            if parsed.scheme not in ['http', 'https']:
                return False
            
            # Check for malicious patterns
            dangerous_patterns = [
                'javascript:', 'data:', 'file:', 'ftp:',
                'localhost', '127.0.0.1', '0.0.0.0',
                '192.168.', '10.', '172.16.', '172.17.',
                '172.18.', '172.19.', '172.20.', '172.21.',
                '172.22.', '172.23.', '172.24.', '172.25.',
                '172.26.', '172.27.', '172.28.', '172.29.',
                '172.30.', '172.31.'
            ]
            
            url_lower = url.lower()
            if any(pattern in url_lower for pattern in dangerous_patterns):
                return False
            
            # Check domain length and format
            if len(parsed.netloc) > 253 or not parsed.netloc:
                return False
            
            return True
            
        except Exception:
            return False
    
    async def crawl_website(self, start_url: str, crawl_options: CrawlOptions, depth: int = 0) -> List[ScrapedContent]:
        """
        Crawl a website with comprehensive options and safety measures
        """
        if depth > crawl_options.maxDepth or len(self.visited_urls) >= crawl_options.maxPages:
            return []
        
        if start_url in self.visited_urls:
            return []
        
        self.visited_urls.add(start_url)
        results = []
        
        try:
            # Apply rate limiting
            await self.apply_rate_limit(start_url)
            
            # Scrape current page
            content = await self.scrape_single_page(start_url)
            content.metadata['crawlDepth'] = depth
            content.metadata['parentUrl'] = start_url if depth == 0 else None
            results.append(content)
            
            # Find related links on the same domain
            if depth < crawl_options.maxDepth:
                related_links = await self.extract_related_links(
                    start_url, 
                    crawl_options.includeSubdomains
                )
                
                # Crawl related pages with concurrency control
                semaphore = asyncio.Semaphore(3)  # Max 3 concurrent requests
                tasks = []
                
                for link in related_links[:min(5, crawl_options.maxPages - len(self.visited_urls))]:
                    if len(self.visited_urls) < crawl_options.maxPages:
                        task = self._crawl_with_semaphore(
                            semaphore, link, crawl_options, depth + 1
                        )
                        tasks.append(task)
                
                # Wait for all tasks to complete
                if tasks:
                    sub_results_list = await asyncio.gather(*tasks, return_exceptions=True)
                    for sub_results in sub_results_list:
                        if isinstance(sub_results, list):
                            results.extend(sub_results)
                        elif isinstance(sub_results, Exception):
                            logger.warning(f"Crawl task failed: {sub_results}")
            
        except Exception as e:
            logger.warning(f"Failed to crawl {start_url}: {e}")
        
        return results
    
    async def _crawl_with_semaphore(self, semaphore: asyncio.Semaphore, 
                                   url: str, crawl_options: CrawlOptions, depth: int):
        """Crawl with semaphore for concurrency control"""
        async with semaphore:
            return await self.crawl_website(url, crawl_options, depth)
    
    async def extract_related_links(self, url: str, include_subdomains: bool = False) -> List[str]:
        """
        Extract related links with comprehensive filtering and validation
        """
        try:
            async with self.session.get(url) as response:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                base_domain = urlparse(url).netloc
                base_scheme = urlparse(url).scheme
                links = []
                
                # Enhanced link extraction with multiple selectors
                link_selectors = [
                    'a[href]',
                    'area[href]',
                    'link[rel="canonical"][href]'
                ]
                
                for selector in link_selectors:
                    for element in soup.select(selector):
                        href = element.get('href')
                        if not href:
                            continue
                        
                        # Convert relative URLs to absolute
                        if href.startswith('//'):
                            href = f"{base_scheme}:{href}"
                        elif href.startswith('/'):
                            href = f"{base_scheme}://{base_domain}{href}"
                        elif not href.startswith(('http://', 'https://')):
                            # Handle relative paths
                            from urllib.parse import urljoin
                            href = urljoin(url, href)
                        
                        # Domain filtering
                        parsed_href = urlparse(href)
                        if include_subdomains:
                            # Allow subdomains
                            if not (parsed_href.netloc == base_domain or 
                                   parsed_href.netloc.endswith(f'.{base_domain}')):
                                continue
                        else:
                            # Exact domain match only
                            if parsed_href.netloc != base_domain:
                                continue
                        
                        # Enhanced content filtering
                        excluded_patterns = [
                            # Authentication & User Management
                            'login', 'register', 'signup', 'signin', 'logout',
                            'auth', 'account', 'profile', 'settings',
                            
                            # E-commerce
                            'cart', 'checkout', 'payment', 'order', 'purchase',
                            'shop', 'buy', 'add-to-cart',
                            
                            # Admin & System
                            'admin', 'dashboard', 'control', 'manage',
                            'wp-admin', 'wp-login',
                            
                            # Media & Downloads
                            'download', 'pdf', 'doc', 'zip', 'exe',
                            'image', 'photo', 'gallery',
                            
                            # Social & Interactive
                            'comment', 'reply', 'vote', 'like', 'share',
                            'subscribe', 'newsletter',
                            
                            # Navigation & Utility
                            'search', 'filter', 'sort', 'print',
                            'rss', 'feed', 'sitemap',
                            
                            # File extensions to avoid
                            '.jpg', '.jpeg', '.png', '.gif', '.svg',
                            '.pdf', '.doc', '.docx', '.zip', '.exe',
                            '.mp3', '.mp4', '.avi', '.mov'
                        ]
                        
                        href_lower = href.lower()
                        if any(pattern in href_lower for pattern in excluded_patterns):
                            continue
                        
                        # Avoid fragments and query parameters for content pages
                        clean_href = href.split('#')[0].split('?')[0]
                        if clean_href and clean_href not in [link.split('#')[0].split('?')[0] for link in links]:
                            links.append(href)
                
                # Prioritize content-rich pages
                content_indicators = ['article', 'post', 'blog', 'news', 'story', 'guide', 'tutorial']
                priority_links = []
                regular_links = []
                
                for link in links:
                    if any(indicator in link.lower() for indicator in content_indicators):
                        priority_links.append(link)
                    else:
                        regular_links.append(link)
                
                # Return prioritized list
                return priority_links + regular_links
                
        except Exception as e:
            logger.warning(f"Failed to extract links from {url}: {e}")
            return []
    
    def extract_main_content(self, soup: BeautifulSoup) -> str:
        """
        Extract main content from HTML, filtering out navigation, ads, etc.
        """
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
            script.decompose()
        
        # Try to find main content areas
        main_content = (
            soup.find('main') or 
            soup.find('article') or 
            soup.find('div', class_=lambda x: x and 'content' in x.lower()) or
            soup.find('div', id=lambda x: x and 'content' in x.lower()) or
            soup.body
        )
        
        if main_content:
            return main_content.get_text(strip=True, separator='\n')
        
        return soup.get_text(strip=True, separator='\n')
```

#### 3. RAG Query Service
```python
from langchain import hub
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

class RAGQueryService:
    def __init__(self, vector_store: VectorStore, llm: BaseLLM):
        self.vector_store = vector_store
        self.llm = llm
        self.retriever = vector_store.as_retriever(
            search_kwargs={"k": 5}
        )
        
        # Use modern LCEL approach with create_retrieval_chain
        self.retrieval_qa_prompt = hub.pull("langchain-ai/retrieval-qa-chat")
        self.combine_docs_chain = create_stuff_documents_chain(
            self.llm, 
            self.retrieval_qa_prompt
        )
        self.rag_chain = create_retrieval_chain(
            self.retriever, 
            self.combine_docs_chain
        )
        
        # Alternative LCEL implementation for more control
        def format_docs(docs):
            return "\n\n".join(doc.page_content for doc in docs)
        
        self.custom_rag_chain = (
            {
                "context": self.retriever | format_docs,
                "input": RunnablePassthrough(),
            }
            | self.retrieval_qa_prompt
            | self.llm
            | StrOutputParser()
        )
    
    async def query(self, question: str, filters: Optional[Dict] = None) -> RAGResponse:
        """
        Query using modern LCEL create_retrieval_chain approach
        """
        try:
            # First retrieve documents with similarity scores
            retrieved_docs = await self.retriever.aget_relevant_documents(question)
            
            # Get similarity scores using similarity_search_with_score
            docs_with_scores = await self.vector_store.asimilarity_search_with_score(
                question, k=5
            )
            
            # Use the modern retrieval chain
            result = await self.rag_chain.ainvoke({"input": question})
            
            return RAGResponse(
                answer=result['answer'],
                sources=self.format_sources(docs_with_scores),  # Pass docs with scores
                confidence=self.calculate_confidence(docs_with_scores)
            )
            
        except Exception as e:
            logger.error(f"RAG query failed: {e}")
            raise RAGQueryError(f"Failed to process query: {str(e)}")
    
    async def query_with_streaming(self, question: str) -> AsyncGenerator[str, None]:
        """
        Stream response using LCEL streaming capabilities
        """
        try:
            async for chunk in self.custom_rag_chain.astream(question):
                if isinstance(chunk, str):
                    yield chunk
                    
        except Exception as e:
            logger.error(f"Streaming query failed: {e}")
            yield f"Error: {str(e)}"
    
    def format_sources(self, documents: List[Document]) -> List[DocumentSource]:
        """
        Format retrieved documents into source references
        """
        sources = []
        for doc in documents:
            sources.append(DocumentSource(
                documentId=doc.id,
                documentName=doc.name,
                chunk=doc.metadata.get(summary[:200]) + "..." if len(doc.metadata.get(summary)) > 200 else oc.metadata.get(summary),
                similarity=doc.metadata.get('similarity_score', 0.0),
                url=doc.metadata.get('url')
            ))
        return sources
    
    def calculate_confidence(self, documents_with_scores: List[Tuple[Document, float]]) -> float:
        """
        Calculate confidence score based on retrieved documents with similarity scores
        """
        if not documents_with_scores:
            return 0.0
        
        # Calculate confidence based on actual similarity scores
        similarities = [score for _, score in documents_with_scores]
        
        # Normalize scores (assuming cosine similarity where higher is better)
        # Convert distance to similarity if needed (depends on vector store)
        normalized_scores = [max(0.0, min(1.0, score)) for score in similarities]
        
        # Weighted average with higher weight for top results
        weights = [1.0 / (i + 1) for i in range(len(normalized_scores))]
        weighted_sum = sum(score * weight for score, weight in zip(normalized_scores, weights))
        total_weight = sum(weights)
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
```

## Data Models

### Database Schema

#### Documents Table
```sql
CREATE TABLE documents (
    -- Corresponds to Document.id (Snowflake ID)
    id BIGINT PRIMARY KEY,
    
    -- Corresponds to Document.name
    name VARCHAR(255) NOT NULL,
    
    -- Corresponds to Document.type
    type VARCHAR(50) NOT NULL CHECK (type IN ('pdf', 'docx', 'txt', 'md', 'pptx', 'xlsx', 'csv', 'rtf', 'url')),
    
    -- Corresponds to Document.status
    status VARCHAR(50) NOT NULL DEFAULT 'processing' CHECK (status IN ('processing', 'completed', 'failed')),
    
    -- Corresponds to Document.createdAt
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Corresponds to Document.updatedAt (optional)
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Corresponds to Document.metadata (DocumentMetadata)
    -- Contains size, url, and other metadata based on document type
    metadata JSONB NOT NULL DEFAULT '{}',
    
    -- Indexes for better query performance
    INDEX idx_documents_type (type),
    INDEX idx_documents_status (status),
    INDEX idx_documents_created_at (created_at),
    INDEX idx_documents_metadata_gin (metadata) USING GIN -- For JSONB queries
);

-- DocumentMetadata structure stored in JSONB corresponds to:
/*
File-specific metadata (when type != 'url'):
{
  "originalFileName": "research_paper.pdf",     // DocumentMetadata.originalFileName
  "fileSize": 2048576,                          // DocumentMetadata.fileSize  
  "mimeType": "application/pdf",                // DocumentMetadata.mimeType
  "fileExtension": "pdf",                       // DocumentMetadata.fileExtension
  "chunkCount": 45,                            // DocumentMetadata.chunkCount
  "processingTime": 12.5,                      // DocumentMetadata.processingTime
  "embeddingModel": "text-embedding-ada-002",  // DocumentMetadata.embeddingModel
  "textLength": 15420,                         // DocumentMetadata.textLength
  "language": "en",                            // DocumentMetadata.language
  "tags": ["research", "AI"],                  // DocumentMetadata.tags
  "category": "academic",                      // DocumentMetadata.category
  "summary": "A comprehensive study on...",    // DocumentMetadata.summary
  "keywords": ["neural networks"],             // DocumentMetadata.keywords
  "processingErrors": [],                      // DocumentMetadata.processingErrors
  "lastProcessedAt": "2024-01-15T10:30:00Z",  // DocumentMetadata.lastProcessedAt
  "userTags": ["important", "reference"],     // DocumentMetadata.userTags
  "notes": "Key paper for project X",         // DocumentMetadata.notes
  "customFields": {}                          // DocumentMetadata.customFields
}

Web page metadata (when type = 'url'):
{
  "url": "https://example.com/article",        // DocumentMetadata.url
  "title": "Article Title",                    // DocumentMetadata.title
  "description": "Article description",       // DocumentMetadata.description
  "author": "John Doe",                       // DocumentMetadata.author
  "publishedDate": "2024-01-10T00:00:00Z",   // DocumentMetadata.publishedDate
  "scrapedAt": "2024-01-15T10:30:00Z",       // DocumentMetadata.scrapedAt
  "domain": "example.com",                    // DocumentMetadata.domain
  "crawlDepth": 1,                           // DocumentMetadata.crawlDepth
  "parentUrl": "https://example.com",         // DocumentMetadata.parentUrl
  "relatedUrls": ["https://example.com/2"],  // DocumentMetadata.relatedUrls
  "chunkCount": 25,                          // DocumentMetadata.chunkCount
  "processingTime": 8.3,                     // DocumentMetadata.processingTime
  "embeddingModel": "text-embedding-ada-002", // DocumentMetadata.embeddingModel
  "textLength": 8500,                        // DocumentMetadata.textLength
  "language": "en",                          // DocumentMetadata.language
  "tags": ["web", "article"],               // DocumentMetadata.tags
  "category": "news",                        // DocumentMetadata.category
  "summary": "Summary of the article...",    // DocumentMetadata.summary
  "keywords": ["technology", "AI"],          // DocumentMetadata.keywords
  "processingErrors": [],                    // DocumentMetadata.processingErrors
  "lastProcessedAt": "2024-01-15T10:30:00Z", // DocumentMetadata.lastProcessedAt
  "userTags": ["bookmark"],                  // DocumentMetadata.userTags
  "notes": "Interesting article",           // DocumentMetadata.notes
  "customFields": {}                         // DocumentMetadata.customFields
}
*/
```

#### Document Chunks Storage


**Hybrid with Minimal SQL (Recommended)**
```sql
CREATE TABLE document_chunks (
    id BIGINT PRIMARY KEY,                    -- Snowflake ID
    document_id BIGINT REFERENCES documents(id),
    chunk_index INTEGER NOT NULL,
    vector_id VARCHAR(255) UNIQUE,           -- Reference to vector DB
    start_char INTEGER,
    end_char INTEGER,
    token_count INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Indexes
    INDEX idx_chunks_document_id (document_id),
    INDEX idx_chunks_vector_id (vector_id),
    UNIQUE KEY uk_document_chunk (document_id, chunk_index)
);
```

**Vector Database stores:**
- Embeddings (vectors)
- Text content (for retrieval)
- Minimal metadata for filtering

**SQL Database stores:**
- Chunk relationships and structure
- Processing metadata
- Analytics data


```python
import asyncio
from contextlib import asynccontextmanager
from typing import List, Dict, Optional
import logging

class TransactionManager:
    """Manages distributed transactions across SQL and Vector databases"""
    
    def __init__(self, db_session, vector_store, redis_client):
        self.db = db_session
        self.vector_store = vector_store
        self.redis = redis_client
        self.logger = logging.getLogger(__name__)
    
    @asynccontextmanager
    async def distributed_transaction(self, transaction_id: str):
        """Context manager for distributed transactions"""
        # Start transaction log
        await self.redis.hset(f"tx:{transaction_id}", mapping={
            "status": "started",
            "timestamp": datetime.utcnow().isoformat(),
            "operations": "[]"
        })
        
        operations = []
        try:
            yield operations
            # Commit all operations
            await self._commit_operations(transaction_id, operations)
            await self.redis.hset(f"tx:{transaction_id}", "status", "committed")
        except Exception as e:
            # Rollback all operations
            await self._rollback_operations(transaction_id, operations)
            await self.redis.hset(f"tx:{transaction_id}", "status", "rolled_back")
            raise e
        finally:
            # Cleanup transaction log after 24 hours
            await self.redis.expire(f"tx:{transaction_id}", 86400)
    
    async def _commit_operations(self, transaction_id: str, operations: List[Dict]):
        """Commit all operations in the transaction"""
        for operation in operations:
            if operation["type"] == "sql_commit":
                await self.db.commit()
            elif operation["type"] == "vector_confirm":
                # Vector operations are already committed, just log
                self.logger.info(f"Vector operation confirmed: {operation['details']}")
    
    async def _rollback_operations(self, transaction_id: str, operations: List[Dict]):
        """Rollback all operations in reverse order"""
        for operation in reversed(operations):
            try:
                if operation["type"] == "sql_rollback":
                    await self.db.rollback()
                elif operation["type"] == "vector_delete":
                    # Delete from vector store
                    vector_ids = operation["details"]["vector_ids"]
                    await self.vector_store.adelete(ids=vector_ids)
                    self.logger.info(f"Rolled back vector operations: {vector_ids}")
            except Exception as e:
                self.logger.error(f"Rollback failed for operation {operation}: {e}")

class ChunkStorageManager:
    def __init__(self, db_session, vector_store, redis_client):
        self.db = db_session
        self.vector_store = vector_store
        self.redis = redis_client
        self.tx_manager = TransactionManager(db_session, vector_store, redis_client)
        self.logger = logging.getLogger(__name__)
    
    async def store_document_chunks(self, document_id: int, chunks: List[str], 
                                   document_metadata: dict) -> List[int]:
        """Store chunks with distributed transaction support"""
        transaction_id = f"store_chunks_{document_id}_{int(time.time())}"
        chunk_ids = []
        
        async with self.tx_manager.distributed_transaction(transaction_id) as operations:
            try:
                # Phase 1: Prepare SQL transaction
                async with self.db.begin() as sql_tx:
                    vector_ids_to_rollback = []
                    
                    for i, chunk_text in enumerate(chunks):
                        chunk_id = generate_document_id()  # Snowflake ID
                        
                        # 1. Store in SQL (structure + metadata)
                        sql_chunk = DocumentChunk(
                            id=chunk_id,
                            document_id=document_id,
                            chunk_index=i,
                            vector_id=str(chunk_id),
                            start_char=self.calculate_start_char(chunks, i),
                            end_char=self.calculate_end_char(chunks, i),
                            token_count=len(chunk_text.split())
                        )
                        self.db.add(sql_chunk)
                        
                        # 2. Store in Vector DB (content + embeddings)
                        vector_metadata = {
                            "chunk_id": chunk_id,
                            "document_id": document_id,
                            "document_type": document_metadata.get("type"),
                            "document_name": document_metadata.get("name"),
                            "chunk_index": i,
                            "transaction_id": transaction_id
                        }
                        
                        try:
                            await self.vector_store.aadd_documents([
                                Document(
                                    page_content=chunk_text,
                                    metadata=vector_metadata
                                )
                            ], ids=[str(chunk_id)])
                            
                            vector_ids_to_rollback.append(str(chunk_id))
                            chunk_ids.append(chunk_id)
                            
                        except Exception as e:
                            self.logger.error(f"Vector store operation failed for chunk {chunk_id}: {e}")
                            # Add rollback operation for already stored vectors
                            if vector_ids_to_rollback:
                                operations.append({
                                    "type": "vector_delete",
                                    "details": {"vector_ids": vector_ids_to_rollback}
                                })
                            raise VectorStoreError(f"Failed to store chunk in vector database: {e}")
                    
                    # Phase 2: Commit SQL transaction
                    await sql_tx.commit()
                    operations.append({
                        "type": "sql_commit",
                        "details": {"chunk_ids": chunk_ids}
                    })
                    
                    # Phase 3: Confirm vector operations
                    operations.append({
                        "type": "vector_confirm",
                        "details": {"vector_ids": vector_ids_to_rollback}
                    })
                    
                    # Update document metadata
                    await self._update_document_chunk_count(document_id, len(chunks))
                    
            except Exception as e:
                self.logger.error(f"Failed to store document chunks: {e}")
                # Add rollback operations
                operations.append({
                    "type": "sql_rollback",
                    "details": {"document_id": document_id}
                })
                if chunk_ids:
                    operations.append({
                        "type": "vector_delete",
                        "details": {"vector_ids": [str(cid) for cid in chunk_ids]}
                    })
                raise DocumentProcessingError(f"Failed to store chunks for document {document_id}: {e}")
        
        return chunk_ids
    
    async def _update_document_chunk_count(self, document_id: int, chunk_count: int):
        """Update document metadata with chunk count"""
        try:
            result = await self.db.execute(
                update(Document)
                .where(Document.id == document_id)
                .values(
                    metadata=func.jsonb_set(
                        Document.metadata,
                        '{chunkCount}',
                        str(chunk_count)
                    ),
                    updated_at=func.now()
                )
            )
            await self.db.commit()
        except Exception as e:
            self.logger.error(f"Failed to update document chunk count: {e}")
    
    async def delete_document_chunks(self, document_id: int):
        """Delete chunks with distributed transaction support"""
        transaction_id = f"delete_chunks_{document_id}_{int(time.time())}"
        
        async with self.tx_manager.distributed_transaction(transaction_id) as operations:
            try:
                # Get chunk IDs from SQL
                chunk_result = await self.db.execute(
                    select(DocumentChunk.vector_id)
                    .where(DocumentChunk.document_id == document_id)
                )
                vector_ids = [row[0] for row in chunk_result.fetchall()]
                
                if vector_ids:
                    # Delete from vector database first
                    await self.vector_store.adelete(ids=vector_ids)
                    operations.append({
                        "type": "vector_delete_confirm",
                        "details": {"vector_ids": vector_ids}
                    })
                
                # Delete from SQL
                await self.db.execute(
                    delete(DocumentChunk)
                    .where(DocumentChunk.document_id == document_id)
                )
                await self.db.commit()
                operations.append({
                    "type": "sql_commit",
                    "details": {"document_id": document_id}
                })
                
            except Exception as e:
                self.logger.error(f"Failed to delete document chunks: {e}")
                operations.append({
                    "type": "sql_rollback",
                    "details": {"document_id": document_id}
                })
                raise DocumentProcessingError(f"Failed to delete chunks for document {document_id}: {e}")
    
    async def verify_data_consistency(self, document_id: int) -> Dict[str, Any]:
        """Verify consistency between SQL and Vector databases"""
        try:
            # Get SQL chunk count
            sql_result = await self.db.execute(
                select(func.count(DocumentChunk.id))
                .where(DocumentChunk.document_id == document_id)
            )
            sql_count = sql_result.scalar()
            
            # Get vector chunk count
            vector_result = await self.vector_store.asimilarity_search(
                query="", 
                k=1000,  # Large number to get all
                filter={"document_id": document_id}
            )
            vector_count = len(vector_result)
            
            consistency_report = {
                "document_id": document_id,
                "sql_chunk_count": sql_count,
                "vector_chunk_count": vector_count,
                "is_consistent": sql_count == vector_count,
                "checked_at": datetime.utcnow().isoformat()
            }
            
            if not consistency_report["is_consistent"]:
                self.logger.warning(f"Data inconsistency detected: {consistency_report}")
            
            return consistency_report
            
        except Exception as e:
            self.logger.error(f"Failed to verify data consistency: {e}")
            return {
                "document_id": document_id,
                "error": str(e),
                "checked_at": datetime.utcnow().isoformat()
            }
    
    async def repair_data_consistency(self, document_id: int) -> Dict[str, Any]:
        """Repair data inconsistency between SQL and Vector databases"""
        consistency_report = await self.verify_data_consistency(document_id)
        
        if consistency_report.get("is_consistent", False):
            return {"status": "no_repair_needed", "report": consistency_report}
        
        try:
            # Get SQL chunks
            sql_chunks = await self.db.execute(
                select(DocumentChunk)
                .where(DocumentChunk.document_id == document_id)
                .order_by(DocumentChunk.chunk_index)
            )
            sql_chunk_data = {row.vector_id: row for row in sql_chunks.fetchall()}
            
            # Get vector chunks
            vector_chunks = await self.vector_store.asimilarity_search(
                query="",
                k=1000,
                filter={"document_id": document_id}
            )
            vector_chunk_ids = {doc.metadata.get("chunk_id") for doc in vector_chunks}
            
            # Find missing chunks
            sql_ids = set(sql_chunk_data.keys())
            missing_in_vector = sql_ids - vector_chunk_ids
            missing_in_sql = vector_chunk_ids - sql_ids
            
            repair_actions = []
            
            # Repair missing vector chunks
            if missing_in_vector:
                # This would require re-processing the document
                repair_actions.append(f"Need to re-process document {document_id}")
            
            # Remove orphaned vector chunks
            if missing_in_sql:
                await self.vector_store.adelete(ids=list(missing_in_sql))
                repair_actions.append(f"Removed {len(missing_in_sql)} orphaned vector chunks")
            
            return {
                "status": "repaired",
                "actions": repair_actions,
                "before": consistency_report,
                "after": await self.verify_data_consistency(document_id)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to repair data consistency: {e}")
            return {"status": "repair_failed", "error": str(e)}
```
    



#### Chat Sessions Table
```sql
CREATE TABLE chat_sessions (
    -- Snowflake ID for session
    id BIGINT PRIMARY KEY,
    
    -- For future user management (optional)
    user_id BIGINT,
    
    -- Session creation time
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Last activity time
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Session metadata
    metadata JSONB DEFAULT '{}',
    
    -- Indexes
    INDEX idx_sessions_user_id (user_id),
    INDEX idx_sessions_created_at (created_at)
);

CREATE TABLE chat_messages (
    -- Corresponds to ChatMessage.id (Snowflake ID)
    id BIGINT PRIMARY KEY,
    
    -- References chat session
    session_id BIGINT NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    
    -- Corresponds to ChatMessage.type
    type VARCHAR(20) NOT NULL CHECK (type IN ('user', 'assistant')),
    
    -- Corresponds to ChatMessage.content
    content TEXT NOT NULL,
    
    -- Corresponds to ChatMessage.sources (DocumentSource[])
    sources JSONB DEFAULT '[]',
    
    -- Corresponds to ChatMessage.timestamp
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Indexes for performance
    INDEX idx_messages_session_id (session_id),
    INDEX idx_messages_created_at (created_at),
    INDEX idx_messages_type (type)
);

-- ChatMessage.sources structure in JSONB:
/*
[
  {
    "documentId": 1234567890123456789,        // DocumentSource.documentId (Snowflake ID)
    "documentName": "📄 research_paper.pdf", // DocumentSource.documentName
    "documentType": "pdf",                    // DocumentSource.documentType
    "chunk": "This is the relevant text...", // DocumentSource.chunk
    "similarity": 0.85,                      // DocumentSource.similarity
    "url": null,                             // DocumentSource.url (null for files)
    "chunkIndex": 5,                         // DocumentSource.chunkIndex
    "mimeType": "application/pdf",           // DocumentSource.mimeType
    "author": "John Doe",                    // DocumentSource.author
    "publishedDate": "2024-01-10T00:00:00Z", // DocumentSource.publishedDate
    "category": "academic",                  // DocumentSource.category
    "tags": ["research", "AI"],             // DocumentSource.tags
    "summary": "Research paper summary",     // DocumentSource.summary
    "contextInfo": ["Author: John Doe"],    // DocumentSource.contextInfo
    "domain": null,                          // DocumentSource.domain (null for files)
    "language": "en"                         // DocumentSource.language
  }
]
*/

-- Triggers for automatic updated_at management
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to documents table
CREATE TRIGGER update_documents_updated_at 
    BEFORE UPDATE ON documents 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Apply trigger to chat_sessions table
CREATE TRIGGER update_chat_sessions_updated_at 
    BEFORE UPDATE ON chat_sessions 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();
```

### Vector Database Schema

#### Chroma Collection Configuration
```python
collection_metadata = {
    "hnsw:space": "cosine",           # Cosine similarity for text embeddings
    "hnsw:construction_ef": 200,      # Higher ef for better recall
    "hnsw:M": 16,                     # Balanced performance/memory
    "hnsw:max_elements": 1000000      # Support up to 1M chunks
}

# Complete chunk metadata schema stored with each vector
chunk_metadata_schema = {
    # Document identification
    "document_id": "int64",           # Snowflake ID of parent document
    "document_name": "string",        # Display name
    "document_type": "string",        # pdf|docx|txt|md|pptx|xlsx|csv|rtf|url
    "document_url": "string|null",    # URL for web pages
    
    # Chunk identification  
    "chunk_id": "int64",              # Unique Snowflake ID for chunk
    "chunk_index": "int",             # Position within document (0-based)
    "chunk_content": "string",        # Full text content of chunk
    
    # Text positioning
    "start_char": "int",              # Start character position in document
    "end_char": "int",                # End character position in document
    "token_count": "int",             # Number of tokens in chunk
    
    # Processing metadata
    "embedding_model": "string",      # Model used for embedding
    "created_at": "string",           # ISO timestamp
    "language": "string",             # Detected language
    
    # Document metadata (denormalized for fast access)
    "author": "string|null",          # Document author
    "category": "string|null",        # Document category
    "tags": "array[string]",          # Document tags
    "domain": "string|null",          # Domain for web pages
    "mime_type": "string|null",       # File MIME type
    "published_date": "string|null",  # Publication date
    
    # User metadata
    "user_tags": "array[string]",     # User-defined tags
    "notes": "string|null"            # User notes for chunk
}
```

#### Vector Database Integration
The vector database operations are handled by the `ChunkStorageManager` class defined above, which provides:
- Unified chunk storage across SQL and vector databases
- Consistent ID management using Snowflake IDs
- Atomic operations for data consistency
- Optimized query performance with minimal metadata

## Error Handling

### Comprehensive Error Types and Responses

```python
from enum import Enum
from typing import Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import logging

class ErrorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    VALIDATION = "validation"
    PROCESSING = "processing"
    NETWORK = "network"
    STORAGE = "storage"
    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    SYSTEM = "system"

class RAGSystemError(Exception):
    """Base exception for RAG system errors"""
    def __init__(self, message: str, error_code: str = None, 
                 category: ErrorCategory = ErrorCategory.SYSTEM,
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                 details: Dict = None, recoverable: bool = True):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.category = category
        self.severity = severity
        self.details = details or {}
        self.recoverable = recoverable
        self.timestamp = datetime.utcnow()

class DocumentProcessingError(RAGSystemError):
    """Raised when document processing fails"""
    def __init__(self, message: str, document_id: int = None, **kwargs):
        super().__init__(message, category=ErrorCategory.PROCESSING, **kwargs)
        self.document_id = document_id

class VectorStoreError(RAGSystemError):
    """Raised when vector database operations fail"""
    def __init__(self, message: str, operation: str = None, **kwargs):
        super().__init__(message, category=ErrorCategory.STORAGE, **kwargs)
        self.operation = operation

class LLMError(RAGSystemError):
    """Raised when LLM operations fail"""
    def __init__(self, message: str, model: str = None, **kwargs):
        super().__init__(message, category=ErrorCategory.PROCESSING, **kwargs)
        self.model = model

class ScrapingError(RAGSystemError):
    """Raised when web scraping fails"""
    def __init__(self, message: str, url: str = None, **kwargs):
        super().__init__(message, category=ErrorCategory.NETWORK, **kwargs)
        self.url = url

class SecurityError(RAGSystemError):
    """Raised for security-related issues"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.AUTHENTICATION, 
                        severity=ErrorSeverity.HIGH, recoverable=False, **kwargs)

class RateLimitError(RAGSystemError):
    """Raised when rate limits are exceeded"""
    def __init__(self, message: str, retry_after: int = None, **kwargs):
        super().__init__(message, category=ErrorCategory.RATE_LIMIT, **kwargs)
        self.retry_after = retry_after

# Error response format
@dataclass
class ErrorResponse:
    error_code: str
    message: str
    category: str
    severity: str
    recoverable: bool
    details: Optional[Dict] = None
    timestamp: datetime = None
    request_id: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

class ErrorHandler:
    """Centralized error handling with recovery strategies"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.error_counts = {}  # Track error frequencies
        self.circuit_breakers = {}  # Circuit breaker states
        
    def handle_error(self, error: Exception, context: Dict = None) -> ErrorResponse:
        """Handle errors with appropriate recovery strategies"""
        context = context or {}
        
        if isinstance(error, RAGSystemError):
            return self._handle_rag_error(error, context)
        else:
            return self._handle_generic_error(error, context)
    
    def _handle_rag_error(self, error: RAGSystemError, context: Dict) -> ErrorResponse:
        """Handle RAG-specific errors"""
        # Log error with context
        self.logger.error(
            f"RAG Error: {error.message}",
            extra={
                "error_code": error.error_code,
                "category": error.category.value,
                "severity": error.severity.value,
                "details": error.details,
                "context": context
            }
        )
        
        # Update error tracking
        self._track_error(error.error_code)
        
        # Apply recovery strategy
        recovery_action = self._get_recovery_action(error)
        
        return ErrorResponse(
            error_code=error.error_code,
            message=self._get_user_friendly_message(error),
            category=error.category.value,
            severity=error.severity.value,
            recoverable=error.recoverable,
            details={
                **error.details,
                "recovery_action": recovery_action,
                "context": context
            },
            timestamp=error.timestamp,
            request_id=context.get("request_id")
        )
    
    def _get_user_friendly_message(self, error: RAGSystemError) -> str:
        """Convert technical errors to user-friendly messages"""
        message_map = {
            "DocumentProcessingError": "Failed to process document. Please check the file format and try again.",
            "VectorStoreError": "Database temporarily unavailable. Please try again in a few moments.",
            "LLMError": "AI service temporarily unavailable. Please try again later.",
            "ScrapingError": "Unable to access the webpage. Please check the URL and try again.",
            "SecurityError": "Security validation failed. Please verify your request.",
            "RateLimitError": "Too many requests. Please wait before trying again."
        }
        return message_map.get(error.error_code, error.message)
    
    def _get_recovery_action(self, error: RAGSystemError) -> str:
        """Determine appropriate recovery action"""
        if error.category == ErrorCategory.NETWORK:
            return "retry_with_backoff"
        elif error.category == ErrorCategory.PROCESSING:
            return "retry_with_different_params"
        elif error.category == ErrorCategory.RATE_LIMIT:
            return "wait_and_retry"
        elif error.category == ErrorCategory.STORAGE:
            return "use_fallback_storage"
        else:
            return "manual_intervention_required"
    
    def _track_error(self, error_code: str):
        """Track error frequency for circuit breaker logic"""
        self.error_counts[error_code] = self.error_counts.get(error_code, 0) + 1
        
        # Implement circuit breaker logic
        if self.error_counts[error_code] > 10:  # Threshold
            self.circuit_breakers[error_code] = {
                "state": "open",
                "opened_at": datetime.utcnow()
            }
```

### Advanced Retry Mechanisms with Circuit Breaker

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import asyncio
from datetime import datetime, timedelta

class CircuitBreaker:
    """Circuit breaker pattern implementation"""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half-open"
            else:
                raise CircuitBreakerOpenError("Circuit breaker is open")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt reset"""
        if self.last_failure_time is None:
            return True
        return datetime.utcnow() - self.last_failure_time > timedelta(seconds=self.timeout)
    
    def _on_success(self):
        """Handle successful operation"""
        self.failure_count = 0
        self.state = "closed"
    
    def _on_failure(self):
        """Handle failed operation"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"

class CircuitBreakerOpenError(Exception):
    pass

# Enhanced retry decorators
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((VectorStoreError, LLMError)),
    reraise=True
)
async def process_with_retry(operation: Callable, *args, **kwargs):
    """Retry mechanism for critical operations"""
    return await operation(*args, **kwargs)

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=1, max=30),
    retry=retry_if_exception_type(ScrapingError),
    reraise=True
)
async def scrape_with_retry(operation: Callable, *args, **kwargs):
    """Retry mechanism for web scraping operations"""
    return await operation(*args, **kwargs)

# Graceful degradation strategies
class GracefulDegradation:
    """Implement graceful degradation for system resilience"""
    
    @staticmethod
    async def fallback_vector_search(query: str, primary_store, fallback_store):
        """Fallback to secondary vector store if primary fails"""
        try:
            return await primary_store.similarity_search(query)
        except VectorStoreError:
            logger.warning("Primary vector store failed, using fallback")
            return await fallback_store.similarity_search(query)
    
    @staticmethod
    async def fallback_llm_response(query: str, primary_llm, fallback_llm):
        """Fallback to secondary LLM if primary fails"""
        try:
            return await primary_llm.agenerate([query])
        except LLMError:
            logger.warning("Primary LLM failed, using fallback")
            return await fallback_llm.agenerate([query])
    
    @staticmethod
    def cached_response(cache_key: str, cache_store) -> Optional[str]:
        """Return cached response if available"""
        try:
            return cache_store.get(cache_key)
        except Exception:
            return None
```

## Testing Strategy

### Unit Testing
- **Frontend**: Vue Test Utils with Jest
- **Backend**: pytest with async support
- **Services**: Mock external dependencies (LLM, vector DB)

### Integration Testing
- **API Testing**: FastAPI TestClient
- **Database Testing**: Test database with fixtures
- **Vector Store Testing**: In-memory vector store for tests

### End-to-End Testing
- **Playwright**: Full user journey testing
- **Document Processing**: Test with sample documents
- **RAG Pipeline**: Test complete question-answering flow

### Performance Testing
- **Load Testing**: Locust for concurrent user simulation
- **Vector Search**: Benchmark similarity search performance
- **Memory Usage**: Monitor embedding and chunking memory consumption

## Security Considerations

### Input Validation
```python
from pydantic import BaseModel, validator, HttpUrl
from typing import List

class DocumentUploadRequest(BaseModel):
    files: List[UploadFile]
    
    @validator('files')
    def validate_files(cls, v):
        allowed_types = {
            'application/pdf': 'pdf',
            'text/plain': 'txt',
            'text/markdown': 'md',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'pptx',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
            'text/csv': 'csv',
            'application/rtf': 'rtf'
        }
        for file in v:
            if file.content_type not in allowed_types:
                raise ValueError(f'File type {file.content_type} not allowed')
            if file.size > 50 * 1024 * 1024:  # 50MB limit
                raise ValueError('File size exceeds 50MB limit')
        return v

class URLRequest(BaseModel):
    url: HttpUrl
    
    @validator('url')
    def validate_url_safety(cls, v):
        # Check against malicious URL patterns
        dangerous_patterns = ['javascript:', 'data:', 'file:']
        if any(pattern in str(v).lower() for pattern in dangerous_patterns):
            raise ValueError('Potentially malicious URL detected')
        return v
```

### Data Encryption
- **At Rest**: Encrypt sensitive document content
- **In Transit**: HTTPS/TLS for all communications
- **Vector Data**: Consider encryption for sensitive embeddings

### Authentication & Authorization
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def get_current_user(token: str = Depends(security)):
    # JWT token validation logic
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

## Configuration Management

### Comprehensive Environment Configuration
```python
from pydantic import BaseSettings, validator, Field
from typing import Optional, List, Dict, Any
import os
from pathlib import Path
import json

class DatabaseSettings(BaseSettings):
    """Database configuration"""
    url: str = Field(..., env="DATABASE_URL")
    pool_size: int = Field(10, env="DB_POOL_SIZE")
    max_overflow: int = Field(20, env="DB_MAX_OVERFLOW")
    pool_timeout: int = Field(30, env="DB_POOL_TIMEOUT")
    pool_recycle: int = Field(3600, env="DB_POOL_RECYCLE")
    echo: bool = Field(False, env="DB_ECHO")
    
    @validator('url')
    def validate_database_url(cls, v):
        if not v.startswith(('postgresql://', 'postgresql+asyncpg://')):
            raise ValueError('Database URL must be PostgreSQL')
        return v

class VectorDatabaseSettings(BaseSettings):
    """Vector database configuration"""
    type: str = Field("chroma", env="VECTOR_DB_TYPE")
    host: str = Field("localhost", env="VECTOR_DB_HOST")
    port: int = Field(8000, env="VECTOR_DB_PORT")
    collection_name: str = Field("rag_documents", env="VECTOR_COLLECTION_NAME")
    
    # Chroma specific
    chroma_persist_directory: Optional[str] = Field(None, env="CHROMA_PERSIST_DIR")
    chroma_client_auth_provider: Optional[str] = Field(None, env="CHROMA_AUTH_PROVIDER")
    chroma_client_auth_credentials: Optional[str] = Field(None, env="CHROMA_AUTH_CREDENTIALS")
    
    # Pinecone specific
    pinecone_api_key: Optional[str] = Field(None, env="PINECONE_API_KEY")
    pinecone_environment: Optional[str] = Field(None, env="PINECONE_ENVIRONMENT")
    pinecone_index_name: Optional[str] = Field(None, env="PINECONE_INDEX_NAME")
    
    @validator('type')
    def validate_vector_db_type(cls, v):
        allowed_types = ['chroma', 'pinecone', 'weaviate', 'qdrant']
        if v not in allowed_types:
            raise ValueError(f'Vector DB type must be one of {allowed_types}')
        return v

class LLMSettings(BaseSettings):
    """LLM configuration"""
    provider: str = Field("openai", env="LLM_PROVIDER")
    model_name: str = Field("gpt-3.5-turbo", env="LLM_MODEL_NAME")
    temperature: float = Field(0.7, env="LLM_TEMPERATURE")
    max_tokens: int = Field(2000, env="LLM_MAX_TOKENS")
    timeout: int = Field(60, env="LLM_TIMEOUT")
    
    # OpenAI specific
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    openai_organization: Optional[str] = Field(None, env="OPENAI_ORGANIZATION")
    openai_base_url: Optional[str] = Field(None, env="OPENAI_BASE_URL")
    
    # Anthropic specific
    anthropic_api_key: Optional[str] = Field(None, env="ANTHROPIC_API_KEY")
    
    # Local model specific
    local_model_path: Optional[str] = Field(None, env="LOCAL_MODEL_PATH")
    local_model_device: str = Field("cpu", env="LOCAL_MODEL_DEVICE")
    
    @validator('provider')
    def validate_llm_provider(cls, v):
        allowed_providers = ['openai', 'anthropic', 'local', 'azure', 'huggingface']
        if v not in allowed_providers:
            raise ValueError(f'LLM provider must be one of {allowed_providers}')
        return v
    
    @validator('temperature')
    def validate_temperature(cls, v):
        if not 0 <= v <= 2:
            raise ValueError('Temperature must be between 0 and 2')
        return v

class EmbeddingSettings(BaseSettings):
    """Embedding model configuration"""
    provider: str = Field("openai", env="EMBEDDING_PROVIDER")
    model_name: str = Field("text-embedding-ada-002", env="EMBEDDING_MODEL_NAME")
    batch_size: int = Field(100, env="EMBEDDING_BATCH_SIZE")
    timeout: int = Field(60, env="EMBEDDING_TIMEOUT")
    
    # OpenAI specific
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    
    # HuggingFace specific
    huggingface_model_name: Optional[str] = Field(None, env="HF_EMBEDDING_MODEL")
    huggingface_device: str = Field("cpu", env="HF_EMBEDDING_DEVICE")
    
    @validator('provider')
    def validate_embedding_provider(cls, v):
        allowed_providers = ['openai', 'huggingface', 'sentence-transformers', 'cohere']
        if v not in allowed_providers:
            raise ValueError(f'Embedding provider must be one of {allowed_providers}')
        return v

class SecuritySettings(BaseSettings):
    """Security configuration"""
    secret_key: str = Field(..., env="SECRET_KEY")
    jwt_algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    
    # CORS settings
    cors_origins: List[str] = Field(["*"], env="CORS_ORIGINS")
    cors_methods: List[str] = Field(["*"], env="CORS_METHODS")
    cors_headers: List[str] = Field(["*"], env="CORS_HEADERS")
    
    # Rate limiting
    rate_limit_requests: int = Field(100, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(60, env="RATE_LIMIT_WINDOW")  # seconds
    
    # File upload security
    max_file_size: int = Field(50 * 1024 * 1024, env="MAX_FILE_SIZE")  # 50MB
    allowed_file_types: List[str] = Field([
        "application/pdf", "text/plain", "text/markdown",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/csv", "application/rtf"
    ], env="ALLOWED_FILE_TYPES")
    
    # Malware scanning
    enable_malware_scan: bool = Field(True, env="ENABLE_MALWARE_SCAN")
    clamav_host: str = Field("localhost", env="CLAMAV_HOST")
    clamav_port: int = Field(3310, env="CLAMAV_PORT")
    
    @validator('secret_key')
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError('Secret key must be at least 32 characters long')
        return v
    
    @validator('cors_origins', pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v

class RedisSettings(BaseSettings):
    """Redis configuration"""
    url: str = Field("redis://localhost:6379", env="REDIS_URL")
    max_connections: int = Field(20, env="REDIS_MAX_CONNECTIONS")
    retry_on_timeout: bool = Field(True, env="REDIS_RETRY_ON_TIMEOUT")
    health_check_interval: int = Field(30, env="REDIS_HEALTH_CHECK_INTERVAL")
    
    # Cache settings
    default_ttl: int = Field(3600, env="REDIS_DEFAULT_TTL")  # 1 hour
    session_ttl: int = Field(86400, env="REDIS_SESSION_TTL")  # 24 hours

class StorageSettings(BaseSettings):
    """File storage configuration"""
    upload_dir: Path = Field(Path("./uploads"), env="UPLOAD_DIR")
    temp_dir: Path = Field(Path("./temp"), env="TEMP_DIR")
    backup_dir: Optional[Path] = Field(None, env="BACKUP_DIR")
    
    # Storage cleanup
    cleanup_temp_files_hours: int = Field(24, env="CLEANUP_TEMP_FILES_HOURS")
    cleanup_failed_uploads_hours: int = Field(1, env="CLEANUP_FAILED_UPLOADS_HOURS")
    
    @validator('upload_dir', 'temp_dir', 'backup_dir', pre=True)
    def create_directories(cls, v):
        if v is not None:
            path = Path(v)
            path.mkdir(parents=True, exist_ok=True)
            return path
        return v

class MonitoringSettings(BaseSettings):
    """Monitoring and observability configuration"""
    enable_metrics: bool = Field(True, env="ENABLE_METRICS")
    metrics_port: int = Field(8001, env="METRICS_PORT")
    
    # Logging
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_format: str = Field("json", env="LOG_FORMAT")  # json or text
    log_file: Optional[str] = Field(None, env="LOG_FILE")
    
    # Sentry
    sentry_dsn: Optional[str] = Field(None, env="SENTRY_DSN")
    sentry_environment: str = Field("development", env="SENTRY_ENVIRONMENT")
    
    # Health checks
    health_check_timeout: int = Field(5, env="HEALTH_CHECK_TIMEOUT")
    
    @validator('log_level')
    def validate_log_level(cls, v):
        allowed_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in allowed_levels:
            raise ValueError(f'Log level must be one of {allowed_levels}')
        return v.upper()

class WebScrapingSettings(BaseSettings):
    """Web scraping configuration"""
    max_depth: int = Field(2, env="SCRAPING_MAX_DEPTH")
    max_pages: int = Field(10, env="SCRAPING_MAX_PAGES")
    request_timeout: int = Field(30, env="SCRAPING_TIMEOUT")
    request_delay: float = Field(1.0, env="SCRAPING_DELAY")
    
    # User agent
    user_agent: str = Field("RAG-System-Bot/1.0", env="SCRAPING_USER_AGENT")
    
    # Playwright settings
    enable_playwright: bool = Field(True, env="ENABLE_PLAYWRIGHT")
    playwright_timeout: int = Field(30000, env="PLAYWRIGHT_TIMEOUT")  # milliseconds
    
    # Content filtering
    min_content_length: int = Field(100, env="MIN_CONTENT_LENGTH")
    max_content_length: int = Field(1000000, env="MAX_CONTENT_LENGTH")  # 1MB

class Settings(BaseSettings):
    """Main application settings"""
    app_name: str = Field("RAG System", env="APP_NAME")
    app_version: str = Field("1.0.0", env="APP_VERSION")
    environment: str = Field("development", env="ENVIRONMENT")
    debug: bool = Field(False, env="DEBUG")
    
    # Sub-configurations
    database: DatabaseSettings = DatabaseSettings()
    vector_db: VectorDatabaseSettings = VectorDatabaseSettings()
    llm: LLMSettings = LLMSettings()
    embedding: EmbeddingSettings = EmbeddingSettings()
    security: SecuritySettings = SecuritySettings()
    redis: RedisSettings = RedisSettings()
    storage: StorageSettings = StorageSettings()
    monitoring: MonitoringSettings = MonitoringSettings()
    scraping: WebScrapingSettings = WebScrapingSettings()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
    @validator('environment')
    def validate_environment(cls, v):
        allowed_envs = ['development', 'staging', 'production', 'testing']
        if v not in allowed_envs:
            raise ValueError(f'Environment must be one of {allowed_envs}')
        return v
    
    def is_production(self) -> bool:
        return self.environment == "production"
    
    def is_development(self) -> bool:
        return self.environment == "development"

# Configuration factory
class ConfigurationManager:
    """Manages configuration loading and validation"""
    
    def __init__(self):
        self._settings: Optional[Settings] = None
        self._config_file_path: Optional[Path] = None
    
    def load_settings(self, config_file: Optional[str] = None) -> Settings:
        """Load settings with optional config file override"""
        if config_file:
            self._config_file_path = Path(config_file)
            if not self._config_file_path.exists():
                raise FileNotFoundError(f"Configuration file not found: {config_file}")
        
        try:
            self._settings = Settings()
            self._validate_configuration()
            return self._settings
        except Exception as e:
            raise ValueError(f"Configuration validation failed: {e}")
    
    def _validate_configuration(self):
        """Validate configuration consistency"""
        if not self._settings:
            return
        
        # Validate API keys based on providers
        if self._settings.llm.provider == "openai" and not self._settings.llm.openai_api_key:
            raise ValueError("OpenAI API key is required when using OpenAI LLM provider")
        
        if self._settings.embedding.provider == "openai" and not self._settings.embedding.openai_api_key:
            raise ValueError("OpenAI API key is required when using OpenAI embedding provider")
        
        # Validate vector database configuration
        if self._settings.vector_db.type == "pinecone":
            if not self._settings.vector_db.pinecone_api_key:
                raise ValueError("Pinecone API key is required when using Pinecone")
            if not self._settings.vector_db.pinecone_environment:
                raise ValueError("Pinecone environment is required when using Pinecone")
    
    def get_settings(self) -> Settings:
        """Get current settings"""
        if not self._settings:
            self._settings = self.load_settings()
        return self._settings
    
    def reload_settings(self) -> Settings:
        """Reload settings from environment/file"""
        self._settings = None
        return self.load_settings(str(self._config_file_path) if self._config_file_path else None)
    
    def export_config_template(self, output_file: str):
        """Export configuration template"""
        template = {
            "# Database Configuration": None,
            "DATABASE_URL": "postgresql+asyncpg://user:password@localhost/ragdb",
            "DB_POOL_SIZE": "10",
            
            "# Vector Database Configuration": None,
            "VECTOR_DB_TYPE": "chroma",
            "VECTOR_DB_HOST": "localhost",
            "VECTOR_DB_PORT": "8000",
            
            "# LLM Configuration": None,
            "LLM_PROVIDER": "openai",
            "LLM_MODEL_NAME": "gpt-3.5-turbo",
            "OPENAI_API_KEY": "your-openai-api-key-here",
            
            "# Security Configuration": None,
            "SECRET_KEY": "your-secret-key-here-minimum-32-characters",
            "CORS_ORIGINS": "http://localhost:3000,http://localhost:8080",
            
            "# Redis Configuration": None,
            "REDIS_URL": "redis://localhost:6379",
            
            "# Monitoring Configuration": None,
            "LOG_LEVEL": "INFO",
            "ENABLE_METRICS": "true",
            "SENTRY_DSN": "your-sentry-dsn-here"
        }
        
        with open(output_file, 'w') as f:
            for key, value in template.items():
                if value is None:
                    f.write(f"\n{key}\n")
                else:
                    f.write(f"{key}={value}\n")

# Global configuration manager
config_manager = ConfigurationManager()

# Convenience function to get settings
def get_settings() -> Settings:
    return config_manager.get_settings()

# Hot reload support for development
async def setup_config_hot_reload():
    """Setup configuration hot reload for development"""
    if get_settings().is_development():
        import asyncio
        import watchfiles
        
        async def reload_on_change():
            async for changes in watchfiles.awatch('.env'):
                try:
                    config_manager.reload_settings()
                    print("Configuration reloaded due to .env file changes")
                except Exception as e:
                    print(f"Failed to reload configuration: {e}")
        
        asyncio.create_task(reload_on_change())
```

### Secret Management
```python
import os
from typing import Optional
import boto3
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

class SecretManager:
    """Manages secrets from various providers"""
    
    def __init__(self, provider: str = "env"):
        self.provider = provider
        self._aws_client = None
        self._azure_client = None
    
    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get secret from configured provider"""
        if self.provider == "env":
            return os.getenv(key, default)
        elif self.provider == "aws":
            return self._get_aws_secret(key, default)
        elif self.provider == "azure":
            return self._get_azure_secret(key, default)
        else:
            raise ValueError(f"Unsupported secret provider: {self.provider}")
    
    def _get_aws_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get secret from AWS Secrets Manager"""
        if not self._aws_client:
            self._aws_client = boto3.client('secretsmanager')
        
        try:
            response = self._aws_client.get_secret_value(SecretId=key)
            return response['SecretString']
        except Exception:
            return default
    
    def _get_azure_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get secret from Azure Key Vault"""
        if not self._azure_client:
            vault_url = os.getenv("AZURE_KEY_VAULT_URL")
            if not vault_url:
                return default
            credential = DefaultAzureCredential()
            self._azure_client = SecretClient(vault_url=vault_url, credential=credential)
        
        try:
            secret = self._azure_client.get_secret(key)
            return secret.value
        except Exception:
            return default

# Initialize secret manager
secret_manager = SecretManager(provider=os.getenv("SECRET_PROVIDER", "env"))
```

## Monitoring and Observability

### Metrics Collection Strategy

```python
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry
import time
from functools import wraps
import logging
import json
from datetime import datetime

# Prometheus metrics
REGISTRY = CollectorRegistry()

# Request metrics
REQUEST_COUNT = Counter(
    'rag_requests_total',
    'Total number of requests',
    ['endpoint', 'method', 'status'],
    registry=REGISTRY
)

REQUEST_DURATION = Histogram(
    'rag_request_duration_seconds',
    'Request duration in seconds',
    ['endpoint', 'method'],
    registry=REGISTRY
)

# Document processing metrics
DOCUMENT_PROCESSING_TIME = Histogram(
    'rag_document_processing_seconds',
    'Document processing time in seconds',
    ['document_type', 'status'],
    registry=REGISTRY
)

DOCUMENT_COUNT = Gauge(
    'rag_documents_total',
    'Total number of documents',
    ['status'],
    registry=REGISTRY
)

CHUNK_COUNT = Gauge(
    'rag_chunks_total',
    'Total number of chunks',
    registry=REGISTRY
)

# Vector database metrics
VECTOR_SEARCH_TIME = Histogram(
    'rag_vector_search_seconds',
    'Vector search time in seconds',
    registry=REGISTRY
)

VECTOR_SEARCH_RESULTS = Histogram(
    'rag_vector_search_results',
    'Number of results returned by vector search',
    registry=REGISTRY
)

# LLM metrics
LLM_REQUEST_TIME = Histogram(
    'rag_llm_request_seconds',
    'LLM request time in seconds',
    ['model', 'status'],
    registry=REGISTRY
)

LLM_TOKEN_COUNT = Counter(
    'rag_llm_tokens_total',
    'Total number of tokens processed',
    ['model', 'type'],  # type: input/output
    registry=REGISTRY
)

# Error metrics
ERROR_COUNT = Counter(
    'rag_errors_total',
    'Total number of errors',
    ['error_type', 'severity'],
    registry=REGISTRY
)

class MetricsCollector:
    """Centralized metrics collection"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def track_request(self, endpoint: str, method: str, status: int, duration: float):
        """Track HTTP request metrics"""
        REQUEST_COUNT.labels(endpoint=endpoint, method=method, status=status).inc()
        REQUEST_DURATION.labels(endpoint=endpoint, method=method).observe(duration)
    
    def track_document_processing(self, doc_type: str, status: str, duration: float):
        """Track document processing metrics"""
        DOCUMENT_PROCESSING_TIME.labels(document_type=doc_type, status=status).observe(duration)
    
    def track_vector_search(self, duration: float, result_count: int):
        """Track vector search metrics"""
        VECTOR_SEARCH_TIME.observe(duration)
        VECTOR_SEARCH_RESULTS.observe(result_count)
    
    def track_llm_request(self, model: str, status: str, duration: float, 
                         input_tokens: int, output_tokens: int):
        """Track LLM request metrics"""
        LLM_REQUEST_TIME.labels(model=model, status=status).observe(duration)
        LLM_TOKEN_COUNT.labels(model=model, type='input').inc(input_tokens)
        LLM_TOKEN_COUNT.labels(model=model, type='output').inc(output_tokens)
    
    def track_error(self, error_type: str, severity: str):
        """Track error metrics"""
        ERROR_COUNT.labels(error_type=error_type, severity=severity).inc()
    
    def update_document_counts(self, processing: int, completed: int, failed: int):
        """Update document count gauges"""
        DOCUMENT_COUNT.labels(status='processing').set(processing)
        DOCUMENT_COUNT.labels(status='completed').set(completed)
        DOCUMENT_COUNT.labels(status='failed').set(failed)
    
    def update_chunk_count(self, total_chunks: int):
        """Update chunk count gauge"""
        CHUNK_COUNT.set(total_chunks)

# Metrics decorator
def track_metrics(endpoint: str = None, track_duration: bool = True):
    """Decorator to automatically track metrics"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = 'success'
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = 'error'
                metrics_collector.track_error(
                    error_type=type(e).__name__,
                    severity='high' if isinstance(e, (SecurityError, VectorStoreError)) else 'medium'
                )
                raise
            finally:
                if track_duration and endpoint:
                    duration = time.time() - start_time
                    metrics_collector.track_request(endpoint, 'POST', 200 if status == 'success' else 500, duration)
        
        return wrapper
    return decorator

metrics_collector = MetricsCollector()
```

### Structured Logging Standards

```python
import logging
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional

class StructuredLogger:
    """Structured JSON logging for better observability"""
    
    def __init__(self, name: str, level: int = logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # Remove default handlers
        self.logger.handlers.clear()
        
        # Add structured handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredFormatter())
        self.logger.addHandler(handler)
    
    def info(self, message: str, **kwargs):
        """Log info message with structured data"""
        self.logger.info(message, extra=kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with structured data"""
        self.logger.error(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with structured data"""
        self.logger.warning(message, extra=kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with structured data"""
        self.logger.debug(message, extra=kwargs)

class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logs"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName', 
                          'processName', 'process', 'getMessage']:
                log_entry[key] = value
        
        return json.dumps(log_entry, default=str)

# Application-specific loggers
app_logger = StructuredLogger("rag.app")
processing_logger = StructuredLogger("rag.processing")
vector_logger = StructuredLogger("rag.vector")
llm_logger = StructuredLogger("rag.llm")
security_logger = StructuredLogger("rag.security")
```

### Health Check Endpoints

```python
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import asyncio
import time

health_router = APIRouter(prefix="/health", tags=["health"])

class HealthChecker:
    """Comprehensive health checking"""
    
    def __init__(self, db_session, vector_store, redis_client, llm_service):
        self.db = db_session
        self.vector_store = vector_store
        self.redis = redis_client
        self.llm_service = llm_service
        self.logger = StructuredLogger("rag.health")
    
    async def check_database(self) -> Dict[str, Any]:
        """Check database connectivity and performance"""
        try:
            start_time = time.time()
            result = await self.db.execute(text("SELECT 1"))
            duration = time.time() - start_time
            
            return {
                "status": "healthy",
                "response_time_ms": round(duration * 1000, 2),
                "details": "Database connection successful"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "details": "Database connection failed"
            }
    
    async def check_vector_store(self) -> Dict[str, Any]:
        """Check vector store connectivity and performance"""
        try:
            start_time = time.time()
            # Perform a simple similarity search
            results = await self.vector_store.asimilarity_search("test", k=1)
            duration = time.time() - start_time
            
            return {
                "status": "healthy",
                "response_time_ms": round(duration * 1000, 2),
                "details": f"Vector store responded with {len(results)} results"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "details": "Vector store connection failed"
            }
    
    async def check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity and performance"""
        try:
            start_time = time.time()
            await self.redis.ping()
            duration = time.time() - start_time
            
            return {
                "status": "healthy",
                "response_time_ms": round(duration * 1000, 2),
                "details": "Redis connection successful"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "details": "Redis connection failed"
            }
    
    async def check_llm_service(self) -> Dict[str, Any]:
        """Check LLM service availability"""
        try:
            start_time = time.time()
            # Simple test query
            response = await self.llm_service.agenerate(["Hello"])
            duration = time.time() - start_time
            
            return {
                "status": "healthy",
                "response_time_ms": round(duration * 1000, 2),
                "details": "LLM service responded successfully"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "details": "LLM service unavailable"
            }
    
    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get system performance metrics"""
        try:
            import psutil
            
            return {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent,
                "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
            }
        except ImportError:
            return {"error": "psutil not available"}
        except Exception as e:
            return {"error": str(e)}

health_checker = HealthChecker(db_session, vector_store, redis_client, llm_service)

@health_router.get("/")
async def health_check():
    """Basic health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@health_router.get("/detailed")
async def detailed_health_check():
    """Detailed health check with all components"""
    checks = await asyncio.gather(
        health_checker.check_database(),
        health_checker.check_vector_store(),
        health_checker.check_redis(),
        health_checker.check_llm_service(),
        return_exceptions=True
    )
    
    db_health, vector_health, redis_health, llm_health = checks
    
    overall_status = "healthy"
    if any(check.get("status") == "unhealthy" for check in checks if isinstance(check, dict)):
        overall_status = "degraded"
    
    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "database": db_health,
            "vector_store": vector_health,
            "redis": redis_health,
            "llm_service": llm_health
        },
        "system_metrics": await health_checker.get_system_metrics()
    }

@health_router.get("/metrics")
async def metrics_endpoint():
    """Prometheus metrics endpoint"""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)
```

### Performance Monitoring Tools

```python
import asyncio
import time
from typing import Dict, List, Any
from dataclasses import dataclass, field
from collections import defaultdict, deque

@dataclass
class PerformanceMetric:
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)

class PerformanceMonitor:
    """Real-time performance monitoring"""
    
    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        self.metrics = defaultdict(lambda: deque(maxlen=window_size))
        self.logger = StructuredLogger("rag.performance")
    
    def record_metric(self, name: str, value: float, tags: Dict[str, str] = None):
        """Record a performance metric"""
        metric = PerformanceMetric(
            name=name,
            value=value,
            timestamp=datetime.utcnow(),
            tags=tags or {}
        )
        self.metrics[name].append(metric)
    
    def get_metric_stats(self, name: str, minutes: int = 5) -> Dict[str, Any]:
        """Get statistics for a metric over the last N minutes"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        recent_metrics = [
            m for m in self.metrics[name] 
            if m.timestamp >= cutoff_time
        ]
        
        if not recent_metrics:
            return {"error": "No recent metrics found"}
        
        values = [m.value for m in recent_metrics]
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "p50": self._percentile(values, 50),
            "p95": self._percentile(values, 95),
            "p99": self._percentile(values, 99)
        }
    
    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile"""
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    async def start_monitoring(self):
        """Start background monitoring tasks"""
        asyncio.create_task(self._monitor_system_resources())
        asyncio.create_task(self._monitor_application_metrics())
    
    async def _monitor_system_resources(self):
        """Monitor system resources continuously"""
        while True:
            try:
                import psutil
                
                self.record_metric("system.cpu_percent", psutil.cpu_percent())
                self.record_metric("system.memory_percent", psutil.virtual_memory().percent)
                self.record_metric("system.disk_percent", psutil.disk_usage('/').percent)
                
                # Network I/O
                net_io = psutil.net_io_counters()
                self.record_metric("system.network_bytes_sent", net_io.bytes_sent)
                self.record_metric("system.network_bytes_recv", net_io.bytes_recv)
                
            except Exception as e:
                self.logger.error("Failed to collect system metrics", error=str(e))
            
            await asyncio.sleep(30)  # Collect every 30 seconds
    
    async def _monitor_application_metrics(self):
        """Monitor application-specific metrics"""
        while True:
            try:
                # Document processing queue size
                # This would be implemented based on your queue system
                # self.record_metric("app.processing_queue_size", queue_size)
                
                # Active connections
                # self.record_metric("app.active_connections", connection_count)
                
                pass  # Placeholder for actual implementation
                
            except Exception as e:
                self.logger.error("Failed to collect application metrics", error=str(e))
            
            await asyncio.sleep(60)  # Collect every minute

performance_monitor = PerformanceMonitor()
```

This design provides a robust, scalable foundation for the RAG system with comprehensive monitoring, error handling, data consistency management, and security considerations.