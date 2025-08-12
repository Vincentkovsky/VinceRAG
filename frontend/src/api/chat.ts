import apiClient from './client'
import type { ChatMessage, ChatSession, DocumentSource, ApiResponse } from '@/types'

export interface ChatQueryRequest {
  query: string
  sessionId?: number
  documentIds?: number[]
}

export interface ChatQueryResponse {
  messageId: number
  sessionId: number
  answer: string
  sources: DocumentSource[]
  confidence: number
}

export interface ChatHistoryResponse {
  messages: ChatMessage[]
  session: ChatSession | null
  total: number
}

export const chatApi = {
  // Send message
  async sendMessage(
    query: string,
    sessionId?: number,
    documentIds?: number[]
  ): Promise<ChatQueryResponse> {
    const response = await apiClient.post('/chat/query', {
      query,
      session_id: sessionId,
      document_ids: documentIds,
    })
    return response.data
  },

  // Send streaming message
  async sendStreamingMessage(
    query: string,
    sessionId?: number,
    documentIds?: number[]
  ): Promise<ReadableStream<string>> {
    const response = await fetch(`${apiClient.defaults.baseURL}/chat/query/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
      },
      body: JSON.stringify({
        query,
        session_id: sessionId,
        document_ids: documentIds,
      }),
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('No response body')
    }

    return new ReadableStream({
      start(controller) {
        function pump(): Promise<void> {
          return reader!.read().then(({ done, value }) => {
            if (done) {
              controller.close()
              return
            }

            // Parse SSE data
            const chunk = new TextDecoder().decode(value)
            const lines = chunk.split('\n')
            
            for (const line of lines) {
              if (line.startsWith('data: ')) {
                const data = line.slice(6)
                if (data === '[DONE]') {
                  controller.close()
                  return
                }
                try {
                  const parsed = JSON.parse(data)
                  if (parsed.content) {
                    controller.enqueue(parsed.content)
                  }
                } catch (e) {
                  // Ignore parsing errors for partial chunks
                }
              }
            }

            return pump()
          })
        }

        return pump()
      },
    })
  },

  // Get chat history
  async getChatHistory(sessionId?: number): Promise<ChatHistoryResponse> {
    const params = sessionId ? { session_id: sessionId } : {}
    const response = await apiClient.get('/chat/history', { params })
    return response.data
  },

  // Clear chat history
  async clearChatHistory(sessionId?: number): Promise<ApiResponse<null>> {
    const params = sessionId ? { session_id: sessionId } : {}
    const response = await apiClient.delete('/chat/history', { params })
    return response.data
  },

  // Get chat sessions
  async getChatSessions(): Promise<ChatSession[]> {
    const response = await apiClient.get('/chat/sessions')
    return response.data
  },

  // Create new session
  async createSession(): Promise<ChatSession> {
    const response = await apiClient.post('/chat/sessions')
    return response.data
  },

  // Delete session
  async deleteSession(sessionId: number): Promise<ApiResponse<null>> {
    const response = await apiClient.delete(`/chat/sessions/${sessionId}`)
    return response.data
  },
}