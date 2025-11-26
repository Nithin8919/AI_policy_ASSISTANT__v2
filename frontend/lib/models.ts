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

// Default models - focusing on cloud models since Ollama is not available
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
  },
  {
    id: 'gpt-4o',
    name: 'GPT-4o',
    provider: 'openai',
    type: 'cloud',
    category: 'cloud',
    description: 'Latest OpenAI model with multimodal capabilities',
    capabilities: ['text', 'vision', 'reasoning'],
    maxTokens: 128000,
    costPerToken: 0.00003,
    apiKeyRequired: true,
    isAvailable: false
  },
  {
    id: 'claude-3-5-sonnet-20241022',
    name: 'Claude 3.5 Sonnet',
    provider: 'anthropic',
    type: 'cloud',
    category: 'cloud',
    description: 'Anthropic\'s most capable model for complex tasks',
    capabilities: ['reasoning', 'analysis', 'writing'],
    maxTokens: 200000,
    costPerToken: 0.000015,
    apiKeyRequired: true,
    isAvailable: false
  },
  {
    id: 'gemini-2.5-flash',
    name: 'Gemini 2.5 Flash',
    provider: 'gemini',
    type: 'cloud',
    category: 'cloud',
    description: 'Google\'s fast multimodal model',
    capabilities: ['text', 'vision', 'code'],
    maxTokens: 1000000,
    costPerToken: 0.000001,
    apiKeyRequired: true,
    isAvailable: false
  },
  {
    id: 'gpt-3.5-turbo',
    name: 'GPT-3.5 Turbo',
    provider: 'openai',
    type: 'cloud',
    category: 'cloud',
    description: 'Fast and cost-effective OpenAI model',
    capabilities: ['text', 'reasoning'],
    maxTokens: 16384,
    costPerToken: 0.000002,
    apiKeyRequired: true,
    isAvailable: false
  }
]
