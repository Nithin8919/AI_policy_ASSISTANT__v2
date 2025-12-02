'use client'

import { useState, useRef, useEffect } from 'react'
import { ChatMessage } from '@/components/ChatMessage'
import { ChatInput } from '@/components/ChatInput'
import { TypingIndicator } from '@/components/TypingIndicator'
import { queryAPI, queryModelDirect, type QueryResponse } from '@/lib/api'
import { modelService } from '@/lib/modelService'
import { AIModel } from '@/lib/models'
import { Badge } from '@/components/ui/badge'
import { Server, Cloud } from 'lucide-react'

interface Message {
  id: string
  content: string
  role: 'user' | 'assistant' | 'system'
  timestamp: Date
  response?: QueryResponse
  queryMode?: QueryMode
}

interface ChatBotProps {
  selectedModel: string
  onUpdateChatHistory?: (chatId: string, title: string, preview: string) => void
}

type QueryMode = 'qa' | 'deep_think' | 'brainstorm'

export function ChatBot({ selectedModel, onUpdateChatHistory }: ChatBotProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [queryMode, setQueryMode] = useState<QueryMode>('qa')
  const [internetEnabled, setInternetEnabled] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)


  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isLoading])

  const handleQueryModeChange = (mode: QueryMode) => {
    setQueryMode(mode)
  }

  const handleInternetToggle = (enabled: boolean) => {
    setInternetEnabled(enabled)
  }

  const handleSendMessage = async (content: string) => {
    const userMessage: Message = {
      id: Date.now().toString(),
      content,
      role: 'user',
      timestamp: new Date(),
    }

    setMessages(prev => [...prev, userMessage])
    setIsLoading(true)

    try {
      console.log(`ChatBot: Using query mode: ${queryMode}, Internet: ${internetEnabled}`)

      // Use backend API with current query mode and internet setting
      const response = await queryAPI({
        query: content,
        simulate_failure: false,
        mode: queryMode,
        internet_enabled: internetEnabled
      })

      // Fallback if response.answer is empty or undefined
      const responseContent = response.answer || `I received your message "${content}" but couldn't generate a proper response. This might be due to API configuration issues.`

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: responseContent,
        role: 'assistant',
        timestamp: new Date(),
        response: response,
        queryMode: queryMode,
      }

      setMessages(prev => [...prev, assistantMessage])

      // Update chat history with the first user message
      if (messages.length === 0) {
        const chatId = Date.now().toString()
        const title = content.length > 30 ? content.substring(0, 30) + '...' : content
        const preview = response.answer.length > 50 ? response.answer.substring(0, 50) + '...' : response.answer
        onUpdateChatHistory?.(chatId, title, preview)
      }
    } catch (error) {
      console.error('Chat error:', error)
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: `I apologize, but I encountered an error: ${error instanceof Error ? error.message : 'Unknown error occurred'}`,
        role: 'system',
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex-1 flex flex-col h-full">

      {messages.length === 0 ? (
        /* Initial Empty State - Properly Centered */
        <div className="flex-1 flex flex-col items-center justify-center px-6 py-12">
          {/* Welcome Message */}
          <div className="text-center mb-12">
            <h1 className="text-xl font-light text-foreground/80 tracking-wide">
              How can I help you with education policy today?
            </h1>
          </div>

          {/* Centered Input Field */}
          <div className="w-full max-w-3xl">
            <ChatInput
              onSendMessage={handleSendMessage}
              isLoading={isLoading}
              placeholder="Ask about education policies or say hi..."
              onThinkingModeChange={handleQueryModeChange}
              onInternetToggle={handleInternetToggle}
            />
          </div>
        </div>
      ) : (
        /* Chat Messages State */
        <>
          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto premium-scrollbar">
            <div className="max-w-4xl mx-auto px-6 py-8 space-y-8">
              {messages.map((message) => (
                <ChatMessage key={message.id} message={message} />
              ))}
              {isLoading && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <TypingIndicator />
                  <span>using {queryMode} mode</span>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          </div>

          {/* Chat Input */}
          <div className="px-6 py-6">
            <div className="max-w-4xl mx-auto">
              <ChatInput
                onSendMessage={handleSendMessage}
                isLoading={isLoading}
                placeholder="Ask about education policies or say hi..."
                onThinkingModeChange={handleQueryModeChange}
                onInternetToggle={handleInternetToggle}
              />
            </div>
          </div>
        </>
      )}
    </div>
  )
}
