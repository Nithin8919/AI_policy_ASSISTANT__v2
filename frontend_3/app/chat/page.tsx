'use client'

import { useState, useEffect } from 'react'
import Image from 'next/image'
import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar"
import { ChatBot } from './ChatBot'
import { modelService } from '@/lib/modelService'
import { useLocalChatStore } from '@/hooks/useLocalChatStore'

export default function ChatPage() {
  const { chats, currentChatId, createChat, deleteChat, setCurrentChatId } = useLocalChatStore()
  const [selectedModel, setSelectedModel] = useState<string>("")
  const [isDraftPanelOpen, setIsDraftPanelOpen] = useState(false)

  // Load available models and set default
  useEffect(() => {
    const loadDefaultModel = async () => {
      try {
        console.log('Loading available models for default selection...')
        const allModels = await modelService.refreshModels()
        console.log('Available models:', allModels)

        if (allModels.length > 0) {
          // Prefer cloud models first, then Ollama models
          const cloudModels = allModels.filter(m => m.category === 'cloud' && m.isAvailable)
          const ollamaModels = allModels.filter(m => m.category === 'ollama')

          const defaultModel = cloudModels.length > 0 ? cloudModels[0].id :
            ollamaModels.length > 0 ? ollamaModels[0].id :
              allModels[0].id
          console.log('Setting default model to:', defaultModel)
          setSelectedModel(defaultModel)
        } else {
          console.log('No models available, using fallback')
          setSelectedModel("gemini-2.5-flash")
        }
      } catch (error) {
        console.error('Error loading models:', error)
        setSelectedModel("gemini-2.5-flash")
      }
    }

    loadDefaultModel()
  }, [])

  const handleNewChat = () => {
    createChat()
  }

  const handleSelectChat = (chatId: string) => {
    setCurrentChatId(chatId)
  }

  const handleDeleteChat = (chatId: string) => {
    deleteChat(chatId)
  }

  const handleChatCreated = (chatId: string) => {
    setCurrentChatId(chatId)
  }

  const handleModelChange = (modelId: string) => {
    console.log('Model changed to:', modelId)
    setSelectedModel(modelId)
  }

  // Render the normal chat interface with sidebar and header
  return (
    <SidebarProvider>
      {/* Logo in bottom right corner */}
      <div className="fixed bottom-3 right-3 sm:bottom-6 sm:right-6 z-50">
        <div className="bg-white/10 backdrop-blur-sm rounded-lg p-1.5 sm:p-2 md:p-2.5 border border-white/20">
          <Image
            src="/Techbharat_logo.png"
            alt="TechBharat Logo"
            width={50}
            height={17}
            className="object-contain w-[50px] h-[17px] sm:w-[60px] sm:h-[20px] md:w-[80px] md:h-[27px]"
            priority
            loading="eager"
          />
        </div>
      </div>

      {!isDraftPanelOpen && (
        <AppSidebar
          variant="inset"
          chatHistory={chats.map(chat => ({
            id: chat.id,
            title: chat.title,
            preview: chat.messages.length > 0 
              ? (chat.messages[chat.messages.length - 1].content.substring(0, 50) + (chat.messages[chat.messages.length - 1].content.length > 50 ? '...' : ''))
              : 'No messages yet',
            timestamp: chat.updatedAt,
            messageCount: chat.messages.length
          }))}
          activeChatId={currentChatId || undefined}
          onNewChat={handleNewChat}
          onSelectChat={handleSelectChat}
          onDeleteChat={handleDeleteChat}
        />
      )}
      <SidebarInset className={isDraftPanelOpen ? 'w-full' : ''}>
        <SiteHeader
          selectedModel={selectedModel}
          onModelChange={handleModelChange}
        />

        <div className="flex-1 flex flex-col min-h-0 relative">
          {selectedModel ? (
            <ChatBot
              activeChatId={currentChatId || undefined}
              onChatCreated={handleChatCreated}
              selectedModel={selectedModel}
              onPanelStateChange={setIsDraftPanelOpen}
            />
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <p className="text-muted-foreground">Loading available models...</p>
              </div>
            </div>
          )}
        </div>
      </SidebarInset>
    </SidebarProvider>
  )
}