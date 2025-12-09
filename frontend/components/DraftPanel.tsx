'use client'

import { useState, useEffect, useRef } from 'react'
import { X, Trash2, Download, Upload, ChevronDown } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface DraftPanelProps {
  content: string
  onChange: (content: string) => void
  onClose: () => void
  isMobile?: boolean
}

export function DraftPanel({ content, onChange, onClose, isMobile = false }: DraftPanelProps) {
  const editorRef = useRef<HTMLDivElement>(null)
  const [hasChanges, setHasChanges] = useState(false)
  const [documentTitle, setDocumentTitle] = useState('Draft Document')

  // Restore content from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem('chatbot-draft-content')
    if (saved && !content) {
      onChange(saved)
    }
  }, [])

  // Auto-save to localStorage (debounced 500ms)
  useEffect(() => {
    if (!hasChanges) return

    const timer = setTimeout(() => {
      try {
        localStorage.setItem('chatbot-draft-content', content)
        setHasChanges(false)
      } catch (error) {
        // Handle localStorage quota exceeded
        if (error instanceof DOMException && error.name === 'QuotaExceededError') {
          console.warn('localStorage quota exceeded')
          // Could show a toast notification here
        }
      }
    }, 500)

    return () => clearTimeout(timer)
  }, [content, hasChanges])

  // Sync contentEditable with content prop
  useEffect(() => {
    if (editorRef.current && editorRef.current.textContent !== content) {
      editorRef.current.innerHTML = content || ''
    }
  }, [content])

  const handleInput = (e: React.FormEvent<HTMLDivElement>) => {
    const newContent = e.currentTarget.innerHTML
    onChange(newContent)
    setHasChanges(true)
  }

  const handleClear = () => {
    if (confirm('Are you sure you want to clear all draft content? This cannot be undone.')) {
      onChange('')
      if (editorRef.current) {
        editorRef.current.innerHTML = ''
      }
      localStorage.removeItem('chatbot-draft-content')
      setHasChanges(false)
    }
  }

  const handleDownload = (format: 'txt' | 'html') => {
    const blob = format === 'txt'
      ? new Blob([editorRef.current?.textContent || ''], { type: 'text/plain' })
      : new Blob([editorRef.current?.innerHTML || ''], { type: 'text/html' })

    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `draft-document.${format}`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  // Focus editor on mount
  useEffect(() => {
    if (editorRef.current && !isMobile) {
      // Small delay to ensure panel is fully rendered
      setTimeout(() => {
        editorRef.current?.focus()
      }, 100)
    }
  }, [isMobile])

  return (
    <div
      className={`flex flex-col bg-background border-l border-border ${isMobile ? 'fixed inset-0 z-50 h-full' : 'h-full flex-shrink-0'
        }`}
      role="complementary"
      aria-label="Draft Document Panel"
    >
      {/* Fixed Header - ChatGPT Style */}
      <div className="sticky top-0 z-20 flex items-center justify-between px-4 py-3 border-b border-border bg-background">
        {/* Left: Close button */}
        <Button
          variant="ghost"
          size="icon"
          onClick={onClose}
          className="h-8 w-8 -ml-2"
          aria-label="Close draft panel"
        >
          <X className="h-4 w-4" />
        </Button>

        {/* Center: Title with dropdown */}
        <div className="flex-1 flex items-center justify-center gap-1.5">
          <h2
            className="text-sm font-medium cursor-pointer hover:opacity-80 transition-opacity"
            contentEditable
            suppressContentEditableWarning
            onBlur={(e) => setDocumentTitle(e.currentTarget.textContent || 'Draft Document')}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault()
                e.currentTarget.blur()
              }
            }}
          >
            {documentTitle}
          </h2>
          <ChevronDown className="h-4 w-4 text-muted-foreground" />
        </div>

        {/* Right: Upload and Download */}
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            aria-label="Upload file"
            title="Upload"
          >
            <Upload className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => handleDownload('html')}
            className="h-8 w-8"
            aria-label="Download document"
            title="Download"
          >
            <Download className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Editable Content Area - Independent Scroll with Smooth Behavior */}
      <div
        className="overflow-y-auto bg-muted/20 draft-scrollbar px-4"
        style={{
          scrollBehavior: 'smooth',
          height: 'calc(100vh - 48px - 48px)' // Viewport - Site Header - Draft Panel Header
        }}
      >
        <div className="p-6 max-w-4xl mx-auto">
          <div
            ref={editorRef}
            contentEditable
            suppressContentEditableWarning
            onInput={handleInput}
            className="w-full outline-none prose prose-sm dark:prose-invert max-w-none
                       min-h-[200px] w-full bg-background rounded-lg
                       [&_p]:mb-3 [&_p]:leading-relaxed
                       [&_ul]:list-disc [&_ul]:ml-6 [&_ul]:mb-3
                       [&_ol]:list-decimal [&_ol]:ml-6 [&_ol]:mb-3
                       [&_li]:mb-1
                       [&_h1]:text-2xl [&_h1]:font-bold [&_h1]:mb-4 [&_h1]:mt-6
                       [&_h2]:text-xl [&_h2]:font-semibold [&_h2]:mb-3 [&_h2]:mt-5
                       [&_h3]:text-lg [&_h3]:font-medium [&_h3]:mb-2 [&_h3]:mt-4
                       [&_table]:border-collapse [&_table]:border [&_table]:border-border [&_table]:my-4
                       [&_td]:border [&_td]:border-border [&_td]:p-2
                       [&_th]:border [&_th]:border-border [&_th]:p-2 [&_th]:bg-muted [&_th]:font-semibold
                       [&_code]:bg-muted [&_code]:px-1 [&_code]:py-0.5 [&_code]:rounded [&_code]:text-sm
                       [&_pre]:bg-muted [&_pre]:p-4 [&_pre]:rounded-lg [&_pre]:overflow-x-auto [&_pre]:my-4"
            style={{
              wordBreak: 'break-word',
              whiteSpace: 'pre-wrap'
            }}
            aria-label="Draft document editor"
            role="textbox"
            aria-multiline="true"
          />
        </div>
      </div>
    </div>
  )
}

