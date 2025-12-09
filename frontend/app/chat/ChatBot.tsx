'use client'

import { useState, useRef, useEffect } from 'react'
import { ChatMessage } from '@/components/ChatMessage'
import { ChatInput } from '@/components/ChatInput'
import { TypingIndicator } from '@/components/TypingIndicator'
import { DraftPanel } from '@/components/DraftPanel'
import { FloatingActionButton } from '@/components/FloatingActionButton'
import { queryAPI, queryWithFiles, type QueryResponse, queryModelDirect } from '@/lib/api'
import { modelService } from '@/lib/modelService'
import { AIModel } from '@/lib/models'
import { Badge } from '@/components/ui/badge'
import { Server, Cloud } from 'lucide-react'
import { useChatMessages, useChatStore, Message } from '@/hooks/useChatStore'

interface ChatBotProps {
  selectedModel: string
  activeChatId?: string
  onChatCreated?: (chatId: string) => void
  onPanelStateChange?: (isOpen: boolean) => void
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

export function ChatBot({ selectedModel, activeChatId, onChatCreated, onPanelStateChange }: ChatBotProps) {
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

  // Draft panel state
  const [draftContent, setDraftContent] = useState('')
  const [isPanelOpen, setIsPanelOpen] = useState(false)
  const [isMobile, setIsMobile] = useState(false)

  // Check if mobile on mount and resize
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768)
    }
    checkMobile()
    window.addEventListener('resize', checkMobile)
    return () => window.removeEventListener('resize', checkMobile)
  }, [])

  // Restore draft content from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem('chatbot-draft-content')
    if (saved) {
      setDraftContent(saved)
    }
  }, [])

  const handleCopyToDraft = (content: string) => {
    const separator = draftContent ? '\n\n---\n\n' : ''
    const newContent = `${draftContent}${separator}${content}`
    setDraftContent(newContent)

    // Open panel if closed
    if (!isPanelOpen) {
      setIsPanelOpen(true)
    }
  }

  const togglePanel = () => {
    const newState = !isPanelOpen
    setIsPanelOpen(newState)
    onPanelStateChange?.(newState)
  }

  // Notify parent when panel state changes
  useEffect(() => {
    onPanelStateChange?.(isPanelOpen)
  }, [isPanelOpen, onPanelStateChange])

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
      // If we are just starting, set to initial step
      // If files are present, the first step might be "Analyzing uploaded file..." set by handleSendMessage
      // So only reset if not already set to that.
      if (currentThinkingStep !== "Analyzing uploaded file...") {
        setCurrentThinkingStep(THINKING_STEPS[0])
      }

      interval = setInterval(() => {
        // If we are at the "Analyzing..." step, move to "Understanding..."
        if (currentThinkingStep === "Analyzing uploaded file...") {
          setCurrentThinkingStep(THINKING_STEPS[0])
        } else {
          // Standard cycle
          const currentIndex = THINKING_STEPS.indexOf(currentThinkingStep)
          const nextIndex = (currentIndex + 1) % THINKING_STEPS.length
          setCurrentThinkingStep(THINKING_STEPS[nextIndex])
        }
      }, 2500) // Change step every 2.5 seconds
    }
    return () => clearInterval(interval)
  }, [isSending, currentThinkingStep])

  const handleQueryModeChange = (mode: QueryMode) => {
    setQueryMode(mode)
  }

  const handleInternetToggle = (enabled: boolean) => {
    setInternetEnabled(enabled)
  }

  const handleSendMessage = async (content: string, files?: File[]) => {
    setIsSending(true)

    // Create user message object
    const userMessage: Message = {
      id: Date.now().toString(),
      content,
      role: 'user',
      timestamp: new Date(),
    }

    // Only attach files if they exist and are not empty
    if (files && files.length > 0) {
      userMessage.attachedFiles = files.map(f => ({
        name: f.name,
        size: f.size,
        type: f.type
      }))
    }

    let currentChatId = activeChatId

    try {
      console.log(`ChatBot: Using query mode: ${queryMode}, Internet: ${internetEnabled}, Files attached: ${files?.length || 0}`)

      // If files are present, set initial thinking step
      if (files && files.length > 0) {
        setCurrentThinkingStep("Analyzing uploaded file...")
      }

      // If no active chat, we need to create one
      if (!currentChatId) {
        const title = content.length > 30 ? content.substring(0, 30) + '...' : content
        // We'll update preview later with the answer
        currentChatId = await createChat(userMessage, title, content)
        onChatCreated?.(currentChatId)
      } else {
        await addMessageToChat(currentChatId, userMessage)
      }

      let response: QueryResponse;

      // Build conversation history from previous messages (last 10 messages)
      const conversationHistory = firestoreMessages
        .filter(msg => msg.role === 'user' || msg.role === 'assistant')
        .slice(-10) // Last 10 messages
        .map(msg => ({
          role: msg.role,
          content: msg.content
        }))

      if (files && files.length > 0) {
        // Use file upload endpoint with conversation history
        response = await queryWithFiles(
          content,
          files,
          queryMode,
          internetEnabled,
          conversationHistory
        )
      } else {
        // Use standard endpoint with conversation history
        response = await queryAPI({
          query: content,
          simulate_failure: false,
          mode: queryMode,
          internet_enabled: internetEnabled,
          conversation_history: conversationHistory
        })
      }

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

  // Determine layout classes based on screen size and panel state
  const getLayoutClasses = () => {
    if (!isPanelOpen) {
      return {
        chat: 'w-full',
        panel: 'hidden'
      }
    }

    if (isMobile) {
      return {
        chat: 'w-full',
        panel: 'w-full'
      }
    }

    // Desktop: 60% chat, 40% panel (ChatGPT style)
    return {
      chat: 'w-[60%]',
      panel: 'w-[40%]'
    }
  }

  const layoutClasses = getLayoutClasses()

  return (
    <div className="flex-1 flex flex-col h-full relative">
      {/* Main Content Area - Split Layout with Independent Scrolling */}
      <div className="flex flex-row h-[calc(100vh-48px)] overflow-hidden">
        {/* Chat Area - Independent Scroll */}
        <div className={`${layoutClasses.chat} flex flex-col transition-all duration-300 ${isPanelOpen && !isMobile ? 'border-r border-border' : ''} overflow-hidden`}>
          {!activeChatId && displayMessages.length === 0 ? (
            /* Initial Empty State - Properly Centered */
            <div className="flex-1 flex flex-col items-center justify-center px-6 py-12 h-[calc(100vh-48px)]">
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
              {/* Messages Area - Independent Scroll with Smooth Behavior */}
              <div
                className="overflow-y-auto premium-scrollbar px-4"
                style={{
                  scrollBehavior: 'smooth',
                  height: 'calc(100vh - 48px - 100px)' // Viewport - Header - Input area
                }}
              >
                <div className="max-w-4xl mx-auto px-6 py-8 space-y-8">
                  {displayMessages.map((message) => (
                    <ChatMessage
                      key={message.id}
                      message={message}
                      onCopyToDraft={handleCopyToDraft}
                    />
                  ))}
                  {/* TypingIndicator removed in favor of Thinking Message */}
                  <div ref={messagesEndRef} />
                </div>
              </div>

              {/* Chat Input - Fixed at Bottom */}
              <div className="px-6 py-6 border-t border-border bg-background flex-shrink-0">
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

        {/* Draft Panel - Fixed to Right */}
        {isPanelOpen && (
          <div className={`${layoutClasses.panel} flex-shrink-0 transition-all duration-300 flex flex-col overflow-hidden`}>
            <DraftPanel
              content={draftContent}
              onChange={setDraftContent}
              onClose={togglePanel}
              isMobile={isMobile}
            />
          </div>
        )}
      </div>

      {/* Floating Action Button - Only show when panel is closed */}
      {!isPanelOpen && (
        <FloatingActionButton onClick={togglePanel} />
      )}

      {/* Mobile Overlay */}
      {isMobile && isPanelOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40"
          onClick={togglePanel}
          aria-label="Close draft panel"
        />
      )}
    </div>
  )
}
