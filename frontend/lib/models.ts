export interface AIModel {
  id: string
  name: string
  provider: 'ollama' | 'openai' | 'anthropic' | 'gemini'
  type: 'local' | 'cloud'
  category: 'cloud' | 'ollama'
  description?: string
  capabilities?: string[]
  maxTokens?: number
  costPerToken?: number
  isAvailable?: boolean
}

export interface OllamaModel extends AIModel {
  provider: 'ollama'
  type: 'local'
  size?: string
  downloadUrl?: string
}

export interface CloudModel extends AIModel {
  provider: 'openai' | 'anthropic' | 'gemini'
  type: 'cloud'
  apiKeyRequired?: boolean
  rateLimit?: number
}

export type ModelType = OllamaModel | CloudModel

// Default models - only backend default
export const DEFAULT_MODELS: AIModel[] = [
  {
    id: 'backend-default',
    name: 'Backend Default',
    provider: 'ollama',
    type: 'local',
    category: 'ollama',
    description: 'Uses the backend API default model',
    capabilities: ['text', 'reasoning'],
    maxTokens: 8192,
    isAvailable: true
  }
]
