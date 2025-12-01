'use client'

import { useState, useRef, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Send, Plus, Loader2, Zap, Brain, Lightbulb, Cog, Paperclip, Camera, Search, Image, BookOpen, MoreHorizontal, X } from 'lucide-react'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { 
  DropdownMenu, 
  DropdownMenuContent, 
  DropdownMenuItem, 
  DropdownMenuTrigger, 
  DropdownMenuSeparator 
} from '@/components/ui/dropdown-menu'

interface ChatInputProps {
  onSendMessage: (message: string) => void
  isLoading: boolean
  placeholder?: string
  onThinkingModeChange?: (mode: 'qa' | 'deep_think' | 'brainstorm') => void
}

export function ChatInput({ 
  onSendMessage, 
  isLoading, 
  placeholder = "Ask about education policies or say hi...",
  onThinkingModeChange,
}: ChatInputProps) {
  const [message, setMessage] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const [thinkingMode, setThinkingMode] = useState<'qa' | 'deep_think' | 'brainstorm'>('qa')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!message.trim() || isLoading) return

    onSendMessage(message.trim())
    setMessage('')
    
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value
    setMessage(value)
    
    // Auto-resize textarea
    const textarea = e.target
    textarea.style.height = 'auto'
    textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`
  }

  useEffect(() => {
    // Focus the input when component mounts
    if (textareaRef.current) {
      textareaRef.current.focus()
    }
  }, [])

  const handleThinkingModeChange = (value: 'qa' | 'deep_think' | 'brainstorm') => {
    setThinkingMode(value)
    onThinkingModeChange?.(value)
  }

  const getModeIcon = (mode: 'qa' | 'deep_think' | 'brainstorm') => {
    switch (mode) {
      case 'qa': return <Lightbulb className="h-3 w-3" />
      case 'deep_think': return <Brain className="h-3 w-3" />
      case 'brainstorm': return <Zap className="h-3 w-3" />
      default: return <Lightbulb className="h-3 w-3" />
    }
  }

  const getModeDisplayText = (mode: 'qa' | 'deep_think' | 'brainstorm') => {
    switch (mode) {
      case 'qa': return 'Q&A'
      case 'deep_think': return 'Deep Think'
      case 'brainstorm': return 'Brainstorm'
      default: return 'Q&A'
    }
  }

  const isSpecialMode = thinkingMode !== 'qa'

  return (
    <TooltipProvider>
      <div className="relative">
        {/* Mode Display - always shows current mode */}
        <div className="mb-3 group">
          <div className="flex items-center gap-2 text-sm text-blue-400">
            <div className="flex-shrink-0 w-3 h-3 flex items-center justify-center">
              {getModeIcon(thinkingMode)}
            </div>
            <span>{getModeDisplayText(thinkingMode)} Mode</span>
          </div>
        </div>

        <div className="flex items-end gap-3 bg-background border border-border rounded-2xl p-4 shadow-lg hover:border-border/80 transition-colors">
          {/* Add Button with Dropdown */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button 
                variant="ghost" 
                size="icon"
                className="h-8 w-8 text-muted-foreground hover:text-foreground hover:bg-accent flex-shrink-0"
              >
                <Plus className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="w-64">
              {/* File Options */}
              <DropdownMenuItem>
                <Paperclip className="h-4 w-4 mr-2" />
                Add photos & files
              </DropdownMenuItem>
              <DropdownMenuItem>
                <Camera className="h-4 w-4 mr-2" />
                Take screenshot
              </DropdownMenuItem>
              <DropdownMenuItem>
                <Camera className="h-4 w-4 mr-2" />
                Take photo
              </DropdownMenuItem>
              
              <DropdownMenuSeparator />
              
              {/* Query Mode Options */}
              <DropdownMenuItem 
                onClick={() => handleThinkingModeChange('qa')}
                className={thinkingMode === 'qa' ? 'bg-blue-50 text-blue-600' : ''}
              >
                <Lightbulb className="h-4 w-4 mr-2" />
                Q&A Mode
                {thinkingMode === 'qa' && <span className="ml-auto text-blue-600">✓</span>}
              </DropdownMenuItem>
              <DropdownMenuItem 
                onClick={() => handleThinkingModeChange('deep_think')}
                className={thinkingMode === 'deep_think' ? 'bg-blue-50 text-blue-600' : ''}
              >
                <Brain className="h-4 w-4 mr-2" />
                Deep Think
                {thinkingMode === 'deep_think' && <span className="ml-auto text-blue-600">✓</span>}
              </DropdownMenuItem>
              <DropdownMenuItem 
                onClick={() => handleThinkingModeChange('brainstorm')}
                className={thinkingMode === 'brainstorm' ? 'bg-blue-50 text-blue-600' : ''}
              >
                <Zap className="h-4 w-4 mr-2" />
                Brainstorm
                {thinkingMode === 'brainstorm' && <span className="ml-auto text-blue-600">✓</span>}
              </DropdownMenuItem>
              
              <DropdownMenuSeparator />
              
              <DropdownMenuItem>
                <MoreHorizontal className="h-4 w-4 mr-2" />
                More
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Text Input */}
          <div className="flex-1 relative">
            <textarea
              id="chat-message-input"
              name="message"
              ref={textareaRef}
              value={message}
              onChange={handleInput}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
              disabled={isLoading}
              className="w-full bg-transparent border-0 text-foreground placeholder:text-muted-foreground resize-none focus:outline-none text-base leading-6"
              rows={1}
              style={{ minHeight: '24px', maxHeight: '200px' }}
              aria-label="Chat message input"
            />
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-2 flex-shrink-0">
            {/* Send Button */}
            <Tooltip>
              <TooltipTrigger asChild>
                <Button 
                  onClick={handleSubmit}
                  disabled={isLoading || !message.trim()}
                  className="h-8 w-8 bg-primary hover:bg-primary/90 disabled:bg-muted disabled:text-muted-foreground rounded-full transition-colors"
                  size="icon"
                >
                  {isLoading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Send className="h-4 w-4" />
                  )}
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>{isLoading ? 'Sending...' : 'Send message'}</p>
              </TooltipContent>
            </Tooltip>
          </div>
        </div>

        {/* Subtle hint text */}
        <div className="text-center mt-3">
          <p className="text-xs text-muted-foreground">
            Press Enter to send, Shift+Enter for new line
          </p>
        </div>
      </div>
    </TooltipProvider>
  )
}