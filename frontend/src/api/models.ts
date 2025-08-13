import apiClient from './client'



export interface AIModelConfig {
  embedding_provider: string
  chat_provider: string
  openai_api_key?: string
  openai_base_url: string
  openai_embedding_model: string
  openai_embedding_dimensions: number
  openai_chat_model: string
  qwen_api_key?: string
  qwen_base_url: string
  qwen_embedding_model: string
  qwen_embedding_dimensions: number
  qwen_chat_model: string
  custom_api_key?: string
  custom_base_url: string
  custom_embedding_model: string
  custom_embedding_dimensions: number
  custom_chat_model: string
}

export interface ModelTestResult {
  success: boolean
  message?: string
  error?: string
  embedding_dimensions?: number
}

export const modelsApi = {
  // Get current model configuration
  async getConfig(): Promise<AIModelConfig> {
    const response = await apiClient.get('/admin/models/config')
    return response.data
  },

  // Update model configuration
  async updateConfig(config: AIModelConfig): Promise<{ message: string }> {
    const response = await apiClient.put('/admin/models/config', config)
    return response.data
  },

  // Test model connection
  async testConnection(config: AIModelConfig): Promise<ModelTestResult> {
    const response = await apiClient.post('/admin/models/test', config)
    return response.data
  }
}
