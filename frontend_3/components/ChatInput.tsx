'use client'

import { useState, useRef, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Send, Plus, Loader2, Zap, Brain, Lightbulb, Paperclip, X, Globe, FileText } from 'lucide-react'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator
} from '@/components/ui/dropdown-menu'

interface ChatInputProps {
  onSendMessage: (message: string, files?: File[]) => void
  isLoading: boolean
  placeholder?: string
  onThinkingModeChange?: (mode: 'qa' | 'deep_think' | 'brainstorm') => void
  onInternetToggle?: (enabled: boolean) => void
}

export function ChatInput({
  onSendMessage,
  isLoading,
  placeholder = "Ask about education policies or say hi...",
  onThinkingModeChange,
  onInternetToggle,
}: ChatInputProps) {
  const [message, setMessage] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [thinkingMode, setThinkingMode] = useState<'qa' | 'deep_think' | 'brainstorm'>('qa')
  const [internetEnabled, setInternetEnabled] = useState(false)
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!message.trim() || isLoading) return

    onSendMessage(message.trim(), uploadedFiles.length > 0 ? uploadedFiles : undefined)
    setMessage('')
    setUploadedFiles([])

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

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])

    // Validate file count
    if (uploadedFiles.length + files.length > 3) {
      alert('Maximum 3 files allowed')
      return
    }

    // Validate file types
    const validTypes = ['.pdf', '.txt', '.docx']
    const invalidFiles = files.filter(file => {
      const ext = '.' + file.name.split('.').pop()?.toLowerCase()
      return !validTypes.includes(ext)
    })

    if (invalidFiles.length > 0) {
      alert(`Unsupported file types. Only PDF, TXT, and DOCX files are allowed.`)
      return
    }

    // Validate file sizes (10MB max)
    const oversizedFiles = files.filter(file => file.size > 10 * 1024 * 1024)
    if (oversizedFiles.length > 0) {
      alert(`File too large. Maximum size is 10MB per file.`)
      return
    }

    setUploadedFiles(prev => [...prev, ...files])

    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const removeFile = (index: number) => {
    setUploadedFiles(prev => prev.filter((_, i) => i !== index))
  }

  const handleFileButtonClick = () => {
    fileInputRef.current?.click()
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

  const handleInternetToggle = () => {
    const newValue = !internetEnabled
    setInternetEnabled(newValue)
    onInternetToggle?.(newValue)
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

  const getFileIcon = (filename: string) => {
    const ext = filename.split('.').pop()?.toLowerCase()
    return <FileText className="h-3.5 w-3.5" />
  }

  return (
    <TooltipProvider>
      <div className="relative">
        {/* Mode Display and Internet Toggle */}
        <div className="mb-3 flex items-center justify-between gap-4">
          {/* Mode Display */}
          <div className="flex items-center gap-2 text-sm text-blue-400">
            <div className="flex-shrink-0 w-3 h-3 flex items-center justify-center">
              {getModeIcon(thinkingMode)}
            </div>
            <span>{getModeDisplayText(thinkingMode)} Mode</span>
          </div>

          {/* Internet Toggle Button */}
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleInternetToggle}
                className={`h-7 px-3 gap-2 text-xs font-medium transition-all ${internetEnabled
                    ? 'bg-blue-500/10 text-blue-500 hover:bg-blue-500/20 border border-blue-500/30'
                    : 'text-muted-foreground hover:text-foreground hover:bg-accent border border-transparent'
                  }`}
              >
                <Globe className={`h-3.5 w-3.5 ${internetEnabled ? 'text-blue-500' : ''}`} />
                <span>Internet</span>
                {internetEnabled && (
                  <div className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
                )}
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>{internetEnabled ? 'Internet search enabled' : 'Enable internet search'}</p>
            </TooltipContent>
          </Tooltip>
        </div>

        {/* File Chips */}
        {uploadedFiles.length > 0 && (
          <div className="mb-3 flex flex-wrap gap-2">
            {uploadedFiles.map((file, index) => (
              <div
                key={index}
                className="flex items-center gap-2 px-3 py-1.5 bg-blue-500/10 text-blue-600 rounded-lg border border-blue-500/30 text-xs"
              >
                {getFileIcon(file.name)}
                <span className="max-w-[150px] truncate">{file.name}</span>
                <button
                  onClick={() => removeFile(index)}
                  className="hover:bg-blue-500/20 rounded-full p-0.5 transition-colors"
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="flex items-end gap-3 bg-background border border-border rounded-2xl p-4 shadow-lg hover:border-border/80 transition-colors">
          {/* Hidden file input */}
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.txt,.docx"
            onChange={handleFileSelect}
            className="hidden"
          />

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
              <DropdownMenuItem onClick={handleFileButtonClick}>
                <Paperclip className="h-4 w-4 mr-2" />
                Add files (PDF, TXT, DOCX)
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
            {uploadedFiles.length > 0 && ` • ${uploadedFiles.length} file(s) attached`}
          </p>
        </div>
      </div>
    </TooltipProvider>
  )
}