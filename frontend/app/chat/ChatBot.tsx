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
import { useChatMessages, useChatStore, Message } from '@/hooks/useChatStore'

interface ChatBotProps {
  selectedModel: string
  activeChatId?: string
  onChatCreated?: (chatId: string) => void
}

type QueryMode = 'qa' | 'deep_think' | 'brainstorm'

const THINKING_STEPS = [
  "Understanding your query...",
  "Expanding and rewriting query...",
  "Searching verticals...",
  "Running hybrid retrieval (vector + BM25)...",
  "Checking superseded policies and relations...",
  "Applying rerankers and diversity checks...",
  "Building final results..."
]

export function ChatBot({ selectedModel, activeChatId, onChatCreated }: ChatBotProps) {
  const { messages: firestoreMessages, loadingMessages } = useChatMessages(activeChatId)
  const { createChat, addMessageToChat, updateChatPreview } = useChatStore()

  // Local state for optimistic updates or just rely on Firestore (it's fast enough usually)
  // But for "Thinking..." state we need local state or a way to show pending message.
  // Let's use a local "pending" state.
  const [isSending, setIsSending] = useState(false)
  const [currentThinkingStep, setCurrentThinkingStep] = useState(THINKING_STEPS[0])

  const [queryMode, setQueryMode] = useState<QueryMode>('qa')
  const [internetEnabled, setInternetEnabled] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [firestoreMessages, isSending, currentThinkingStep])

  // Simulated Thinking Process Effect
  useEffect(() => {
    let interval: NodeJS.Timeout
    if (isSending) {
      let stepIndex = 0
      setCurrentThinkingStep(THINKING_STEPS[0])

      interval = setInterval(() => {
        stepIndex = (stepIndex + 1) % THINKING_STEPS.length
        setCurrentThinkingStep(THINKING_STEPS[stepIndex])
      }, 2500) // Change step every 2.5 seconds
    } else {
      setCurrentThinkingStep(THINKING_STEPS[0])
    }
    return () => clearInterval(interval)
  }, [isSending])

  const handleQueryModeChange = (mode: QueryMode) => {
    setQueryMode(mode)
  }

  const handleInternetToggle = (enabled: boolean) => {
    setInternetEnabled(enabled)
  }

  const handleSendMessage = async (content: string) => {
    setIsSending(true)

    // Create user message object
    const userMessage: Message = {
      id: Date.now().toString(),
      content,
      role: 'user',
      timestamp: new Date(),
    }

    let currentChatId = activeChatId

    try {
      console.log(`ChatBot: Using query mode: ${queryMode}, Internet: ${internetEnabled}`)

      // If no active chat, we need to create one, but we usually wait for the response to set the title/preview?
      // Or we can create it now.
      // Let's create it now with the user message.

      if (!currentChatId) {
        const title = content.length > 30 ? content.substring(0, 30) + '...' : content
        // We'll update preview later with the answer
        currentChatId = await createChat(userMessage, title, content)
        onChatCreated?.(currentChatId)
      } else {
        await addMessageToChat(currentChatId, userMessage)
      }

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

      if (currentChatId) {
        await addMessageToChat(currentChatId, assistantMessage)

        // Update preview with the assistant's answer
        const title = content.length > 30 ? content.substring(0, 30) + '...' : content
        const preview = responseContent.length > 50 ? responseContent.substring(0, 50) + '...' : responseContent
        await updateChatPreview(currentChatId, title, preview)
      }

    } catch (error) {
      console.error('Chat error:', error)
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: `I apologize, but I encountered an error: ${error instanceof Error ? error.message : 'Unknown error occurred'}`,
        role: 'system',
        timestamp: new Date(),
      }
      // We might want to add this error message to the chat too
      if (currentChatId) {
        await addMessageToChat(currentChatId, errorMessage)
      }
    } finally {
      setIsSending(false)
    }
  }

  // Combine firestore messages with loading state
  const displayMessages = [...firestoreMessages]

  // Inject optimistic thinking message
  if (isSending) {
    displayMessages.push({
      id: 'thinking-placeholder',
      role: 'assistant',
      content: '', // Empty content, thinking UI handles it
      timestamp: new Date(),
      isThinking: true,
      currentStep: currentThinkingStep,
      queryMode: queryMode
    } as Message)
  }

  return (
    <div className="flex-1 flex flex-col h-full">

      {!activeChatId && displayMessages.length === 0 ? (
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
              isLoading={isSending}
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
              {displayMessages.map((message) => (
                <ChatMessage key={message.id} message={message} />
              ))}
              {/* TypingIndicator removed in favor of Thinking Message */}
              <div ref={messagesEndRef} />
            </div>
          </div>

          {/* Chat Input */}
          <div className="px-6 py-6">
            <div className="max-w-4xl mx-auto">
              <ChatInput
                onSendMessage={handleSendMessage}
                isLoading={isSending}
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
