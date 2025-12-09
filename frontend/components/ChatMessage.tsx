'use client'

import { useState, useRef, useEffect } from 'react'
import { User, Bot, AlertCircle, ChevronDown, ChevronRight, Brain, FileText, CheckCircle2, Copy, Check, Loader2 } from 'lucide-react'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { MarkdownRenderer } from '@/components/MarkdownRenderer'
import { usePdfViewer } from '@/hooks/usePdfViewer'
import { PdfViewer } from '@/components/PdfViewer'

interface Message {
  id: string
  content: string
  role: 'user' | 'assistant' | 'system'
  timestamp: Date
  response?: any
  queryMode?: 'qa' | 'deep_think' | 'brainstorm'
  isThinking?: boolean
  currentStep?: string
  attachedFiles?: { name: string; size: number; type: string }[]
}

interface ChatMessageProps {
  message: Message
  onCopyToDraft?: (content: string) => void
}

// Utility function to format time consistently across server and client
function formatTime(date: Date): string {
  const hours = date.getHours()
  const minutes = date.getMinutes()
  const ampm = hours >= 12 ? 'PM' : 'AM'
  const displayHours = hours % 12 || 12
  const displayMinutes = minutes.toString().padStart(2, '0')
  return `${displayHours}:${displayMinutes} ${ampm}`
}

export function ChatMessage({ message, onCopyToDraft }: ChatMessageProps) {
  const [isThinkingOpen, setIsThinkingOpen] = useState(message.isThinking || false)
  const [copied, setCopied] = useState(false)
  const [showSelectionTooltip, setShowSelectionTooltip] = useState(false)
  const [selectedText, setSelectedText] = useState('')
  const [loadingCitationIndex, setLoadingCitationIndex] = useState<number | null>(null)
  const messageRef = useRef<HTMLDivElement>(null)
  const tooltipRef = useRef<HTMLDivElement>(null)

  // PDF Viewer Hook (temporarily using openPdf instead of openWithSnippet)
  const { state: pdfState, openPdf, closePdf } = usePdfViewer()


  // Handle text selection within this message
  useEffect(() => {
    const handleSelection = () => {
      const selection = window.getSelection()
      if (!selection || selection.rangeCount === 0) {
        setShowSelectionTooltip(false)
        setSelectedText('')
        return
      }

      const range = selection.getRangeAt(0)
      const messageElement = messageRef.current

      // Check if selection is within this message
      if (messageElement && messageElement.contains(range.commonAncestorContainer)) {
        const selectedTextContent = selection.toString().trim()
        if (selectedTextContent && message.role === 'assistant') {
          setSelectedText(selectedTextContent)
          setShowSelectionTooltip(true)
        } else {
          setShowSelectionTooltip(false)
          setSelectedText('')
        }
      } else {
        setShowSelectionTooltip(false)
        setSelectedText('')
      }
    }

    document.addEventListener('mouseup', handleSelection)
    document.addEventListener('selectionchange', handleSelection)

    return () => {
      document.removeEventListener('mouseup', handleSelection)
      document.removeEventListener('selectionchange', handleSelection)
    }
  }, [message.role])

  // Position tooltip near selection
  useEffect(() => {
    if (showSelectionTooltip && tooltipRef.current) {
      const selection = window.getSelection()
      if (selection && selection.rangeCount > 0) {
        const range = selection.getRangeAt(0)
        const rect = range.getBoundingClientRect()
        const tooltip = tooltipRef.current

        // Position tooltip above selection, centered
        tooltip.style.position = 'fixed'
        tooltip.style.top = `${rect.top - 40}px`
        tooltip.style.left = `${rect.left + rect.width / 2}px`
        tooltip.style.transform = 'translateX(-50%)'
      }
    }
  }, [showSelectionTooltip, selectedText])

  // Extract thinking content from message
  const extractThinkingContent = (content: string) => {
    const thinkMatch = content.match(/<think>([\s\S]*?)<\/think>/i)
    return thinkMatch ? thinkMatch[1].trim() : null
  }

  // Clean message content by removing think tags
  const cleanMessageContent = (content: string) => {
    if (!content) return ''
    return content.replace(/<think>[\s\S]*?<\/think>/gi, '').trim()
  }

  // Get HTML content from message (preserve formatting)
  const getMessageHTML = () => {
    if (messageRef.current) {
      const messageElement = messageRef.current.querySelector('[class*="break-words"]')
      if (messageElement) {
        return messageElement.innerHTML
      }
    }
    // Fallback to markdown-rendered content
    return cleanMessageContent(message.content)
  }

  const handleCopyToDraft = (content: string, isHTML: boolean = false) => {
    if (onCopyToDraft) {
      // If HTML, wrap in a div to preserve formatting
      const formattedContent = isHTML ? `<div>${content}</div>` : content
      onCopyToDraft(formattedContent)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const handleCopySelection = () => {
    if (selectedText) {
      handleCopyToDraft(selectedText, false)
      setShowSelectionTooltip(false)
      window.getSelection()?.removeAllRanges()
    }
  }

  const handleCopyFullMessage = () => {
    const htmlContent = getMessageHTML()
    handleCopyToDraft(htmlContent, true)
  }

  // Auto-open thinking for thinking messages
  if (message.isThinking && !isThinkingOpen) {
    setIsThinkingOpen(true)
  }

  // For cloud models, we don't have <think> tags, so we'll show a generic thinking process
  const getThinkingProcessForCloudModel = (queryMode: string) => {
    if (queryMode === 'deep_think') {
      return "This response was generated using deep thinking mode, which encourages step-by-step analysis and multiple perspectives."
    } else if (queryMode === 'brainstorm') {
      return "This response was generated using brainstorm mode, which encourages creative and innovative thinking."
    }
    return null
  }

  const thinkingContent = extractThinkingContent(message.content)
  const cleanContent = cleanMessageContent(message.content)
  const cloudThinkingContent = getThinkingProcessForCloudModel(message.queryMode || '')

  const getAvatarIcon = () => {
    switch (message.role) {
      case 'user':
        return <User className="h-4 w-4" />
      case 'assistant':
        return <Bot className="h-4 w-4" />
      case 'system':
        return <AlertCircle className="h-4 w-4" />
      default:
        return null
    }
  }

  const getInitials = () => {
    switch (message.role) {
      case 'user':
        return 'U'
      case 'assistant':
        return 'AI'
      case 'system':
        return 'S'
      default:
        return '?'
    }
  }

  const isUser = message.role === 'user'
  const isSystem = message.role === 'system'

  return (
    <div className={`flex gap-4 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      {/* Avatar */}
      <Avatar className={`w-8 h-8 ${isUser
        ? 'bg-primary'
        : isSystem
          ? 'bg-destructive'
          : 'bg-secondary'
        }`}>
        <AvatarFallback className={`text-primary-foreground text-sm font-medium ${isUser
          ? 'bg-primary'
          : isSystem
            ? 'bg-destructive'
            : 'bg-secondary'
          }`}>
          {getInitials()}
        </AvatarFallback>
      </Avatar>

      {/* Message Content */}
      <div className={`flex-1 max-w-3xl ${isUser ? 'text-right' : 'text-left'}`} ref={messageRef}>
        <div className={`inline-block rounded-2xl px-4 py-3 text-sm leading-relaxed relative ${isUser
          ? 'bg-primary text-primary-foreground'
          : isSystem
            ? 'bg-destructive/10 text-destructive border border-destructive/20'
            : 'bg-transparent text-foreground p-0' // Transparent for assistant (NotebookLM style)
          }`}>
          {!message.isThinking && (
            <div className="break-words">
              <MarkdownRenderer
                content={cleanContent || message.content || 'Processing your query...'}
                className="text-sm"
              />
            </div>
          )}

          {/* Copy to Page Button - Only for assistant messages */}
          {message.role === 'assistant' && !message.isThinking && onCopyToDraft && (
            <div className="mt-3 flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleCopyFullMessage}
                className="h-7 px-3 text-xs gap-1.5"
                aria-label="Copy entire message to draft document"
              >
                {copied ? (
                  <>
                    <Check className="h-3 w-3" />
                    Copied
                  </>
                ) : (
                  <>
                    <Copy className="h-3 w-3" />
                    Copy to page
                  </>
                )}
              </Button>
            </div>
          )}

          {/* Selection Tooltip */}
          {showSelectionTooltip && selectedText && (
            <div
              ref={tooltipRef}
              className="fixed z-50 bg-background border border-border rounded-lg shadow-lg p-2"
              style={{ pointerEvents: 'auto' }}
            >
              <Button
                variant="default"
                size="sm"
                onClick={handleCopySelection}
                className="h-7 px-3 text-xs gap-1.5"
                aria-label="Copy selected text to draft document"
              >
                <Copy className="h-3 w-3" />
                Copy selection
              </Button>
            </div>
          )}

          {/* Attached Files Display (User Message) - Fixed styling */}
          {message.role === 'user' && message.attachedFiles && message.attachedFiles.length > 0 && (
            <div className="mt-3 space-y-2">
              <div className="text-[10px] font-medium opacity-70 uppercase tracking-wider mb-1">Attached Context</div>
              {message.attachedFiles.map((file, idx) => (
                <div key={idx} className="flex items-center gap-2 bg-white/10 p-2 rounded-lg text-xs backdrop-blur-sm border border-white/10">
                  <div className="p-1.5 bg-white/20 rounded-md">
                    <FileText className="h-3.5 w-3.5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium truncate max-w-[200px]">{file.name}</div>
                    <div className="opacity-70 text-[10px]">Processed</div>
                  </div>
                  <div className="text-green-300">
                    <CheckCircle2 className="h-4 w-4" />
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Show placeholder warning for assistant messages */}
          {message.role === 'assistant' && message.content.includes('N/A') && (
            <div className="mt-3 p-2 bg-amber-500/10 border border-amber-500/20 rounded-lg text-xs text-amber-400">
              <Badge variant="outline" className="text-amber-400 border-amber-500/20 bg-amber-500/10">
                ⚠️ Placeholder Data
              </Badge>
              <p className="mt-1">System not yet connected to vector databases or LLM services.</p>
            </div>
          )}

          {/* Citations Section - NotebookLM Style */}
          {message.role === 'assistant' && Array.isArray(message.response?.citations) && message.response.citations.length > 0 && (
            <div className="mt-6 pt-4 border-t border-border/40">
              <div className="flex items-center gap-2 mb-3">
                <div className="h-4 w-1 bg-primary/60 rounded-full" />
                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Sources</span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {message.response.citations.map((citation: any, index: number) => {
                  const hasUrl = !!citation.url;
                  const displayName = citation.filename || citation.source || citation.docId;
                  const pageInfo = citation.page ? `Page ${citation.page}` : '';
                  const isLoading = loadingCitationIndex === index;

                  const CardContent = () => (
                    <div className="flex items-start gap-3">
                      <div className="flex-shrink-0 flex items-center justify-center w-6 h-6 rounded-full bg-primary/10 text-primary text-[10px] font-bold">
                        {index + 1}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="text-xs font-medium text-foreground truncate pr-2" title={displayName}>
                          {displayName}
                        </div>
                        <div className="text-[11px] text-muted-foreground mt-0.5 line-clamp-2 leading-relaxed group-hover:text-foreground/80 transition-colors">
                          {pageInfo && <span className="font-mono mr-1">[{pageInfo}]</span>}
                          {citation.span}
                        </div>
                      </div>
                      {isLoading && (
                        <div className="flex-shrink-0">
                          <Loader2 className="h-4 w-4 text-primary animate-spin" />
                        </div>
                      )}
                    </div>
                  );

                  // Handle citation click - temporarily skip snippet location
                  const handleCitationClick = async () => {
                    if (hasUrl) return; // Allow default behavior for web links

                    try {
                      setLoadingCitationIndex(index);
                      console.log('Opening PDF for citation:', citation);
                      console.log('Citation fields:', {
                        docId: citation.docId,
                        source: citation.source,
                        filename: citation.filename,
                        url: citation.url
                      });

                      // Try to use filename if available, otherwise use docId
                      const pdfIdentifier = citation.filename || citation.docId;

                      // Temporarily skip snippet location, just open the PDF
                      // Pass citation.source as sourceHint (4th argument)
                      await openPdf(
                        pdfIdentifier,
                        citation.source || displayName,
                        1, // pageNumber
                        citation.source // sourceHint
                      );
                    } catch (error) {
                      console.error('Failed to open PDF:', error);
                      alert(`Failed to open PDF: ${error instanceof Error ? error.message : 'Unknown error'}\n\nThe PDF file may not exist in the storage bucket.`);
                    } finally {
                      setLoadingCitationIndex(null);
                    }
                  };

                  return hasUrl ? (
                    <a
                      key={index}
                      href={citation.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="group relative p-3 rounded-xl bg-card/50 hover:bg-card border border-border/50 hover:border-primary/20 transition-all duration-200 cursor-pointer block"
                    >
                      <CardContent />
                    </a>
                  ) : (
                    <div
                      key={index}
                      onClick={handleCitationClick}
                      className={`group relative p-3 rounded-xl bg-card/50 hover:bg-card border border-border/50 hover:border-primary/20 transition-all duration-200 cursor-pointer hover:shadow-md hover:scale-[1.02] active:scale-[0.98] ${isLoading ? 'opacity-75' : ''}`}
                    >
                      <CardContent />
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Thinking Section for Assistant Messages - Only show for deep thinking modes OR active thinking */}
          {
            message.role === 'assistant' && (
              message.isThinking ||
              ((message.queryMode === 'deep_think' || message.queryMode === 'qa') && (message.response?.processing_trace || thinkingContent || cloudThinkingContent))
            ) && (
              <div className="mt-3">
                <Collapsible open={isThinkingOpen} onOpenChange={setIsThinkingOpen}>
                  <CollapsibleTrigger className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground transition-colors w-full">
                    {isThinkingOpen ? (
                      <ChevronDown className="h-3 w-3" />
                    ) : (
                      <ChevronRight className="h-3 w-3" />
                    )}
                    <Brain className={`h-3 w-3 ${message.isThinking ? 'animate-pulse text-orange-500' : ''}`} />

                    {message.isThinking ? (
                      <span className="font-medium text-orange-600 animate-pulse">
                        {message.currentStep || "Thinking..."}
                      </span>
                    ) : (
                      <span>Thinking process</span>
                    )}
                  </CollapsibleTrigger>
                  <CollapsibleContent className="mt-2">
                    <div className="bg-muted/50 border border-border/50 rounded-lg p-3 text-xs space-y-2">
                      {/* Active Thinking State */}
                      {message.isThinking && (
                        <div className="space-y-2 mb-3">
                          <div className="flex items-center gap-2 text-orange-600">
                            <div className="h-1.5 w-1.5 bg-orange-600 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                            <div className="h-1.5 w-1.5 bg-orange-600 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                            <div className="h-1.5 w-1.5 bg-orange-600 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                          </div>
                        </div>
                      )}
                      {/* Show extracted thinking content or cloud model thinking process */}
                      {(thinkingContent || cloudThinkingContent) && (
                        <div>
                          <span className="font-medium text-foreground">Reasoning:</span>
                          <div className="ml-2 mt-1 text-xs text-muted-foreground">
                            <MarkdownRenderer
                              content={thinkingContent || cloudThinkingContent || ''}
                              className="text-xs"
                            />
                          </div>
                        </div>
                      )}

                      {/* Show processing trace data */}
                      {message.response?.processing_trace && (
                        <>
                          {/* Trace Steps List (ChatGPT Style) */}
                          {message.response.processing_trace.steps && message.response.processing_trace.steps.length > 0 && (
                            <div className="mb-3 pb-3 border-b border-border/50">
                              <span className="font-medium text-foreground block mb-1.5">Processing Steps:</span>
                              <div className="space-y-1.5">
                                {message.response.processing_trace.steps.map((step: string, index: number) => (
                                  <div key={index} className="flex items-start gap-2 text-muted-foreground">
                                    <div className="mt-0.5 min-w-[14px]">
                                      <div className="h-3.5 w-3.5 rounded-full bg-green-500/20 flex items-center justify-center">
                                        <div className="h-1.5 w-2.5 border-l-[1.5px] border-b-[1.5px] border-green-600 -rotate-45 -mt-0.5" />
                                      </div>
                                    </div>
                                    <span>{step}</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {message.response.processing_trace.language && (
                            <div>
                              <span className="font-medium text-foreground">Language:</span>
                              <span className="ml-2 text-muted-foreground">{message.response.processing_trace.language}</span>
                            </div>
                          )}

                          {message.response.processing_trace.retrieval && (
                            <div>
                              <span className="font-medium text-foreground">Retrieval:</span>
                              <div className="ml-2 mt-1 space-y-1">
                                {message.response.processing_trace.retrieval.dense && message.response.processing_trace.retrieval.dense.length > 0 && (
                                  <div>
                                    <span className="text-muted-foreground">Dense:</span>
                                    <div className="ml-2 text-xs text-muted-foreground">
                                      {message.response.processing_trace.retrieval.dense.map((item: string, index: number) => (
                                        <div key={index} className="truncate">• {item}</div>
                                      ))}
                                    </div>
                                  </div>
                                )}
                                {message.response.processing_trace.retrieval.sparse && message.response.processing_trace.retrieval.sparse.length > 0 && (
                                  <div>
                                    <span className="text-muted-foreground">Sparse:</span>
                                    <div className="ml-2 text-xs text-muted-foreground">
                                      {message.response.processing_trace.retrieval.sparse.map((item: string, index: number) => (
                                        <div key={index} className="truncate">• {item}</div>
                                      ))}
                                    </div>
                                  </div>
                                )}
                              </div>
                            </div>
                          )}

                          {message.response.processing_trace.kg_traversal && (
                            <div>
                              <span className="font-medium text-foreground">Knowledge Graph:</span>
                              <div className="ml-2 text-xs text-muted-foreground">
                                {message.response.processing_trace.kg_traversal}
                              </div>
                            </div>
                          )}

                          {message.response.processing_trace.controller_iterations && (
                            <div>
                              <span className="font-medium text-foreground">Controller Iterations:</span>
                              <span className="ml-2 text-muted-foreground">{message.response.processing_trace.controller_iterations}</span>
                            </div>
                          )}
                        </>
                      )}

                      {Array.isArray(message.response?.citations) && message.response.citations.length > 0 && (
                        <div>
                          <span className="font-medium text-foreground">Citations:</span>
                          <div className="ml-2 mt-1 space-y-1 text-muted-foreground">
                            {message.response.citations.map((c: any, i: number) => (
                              <div key={i} className="truncate">• Doc {c.docId} p.{c.page} — {c.span}</div>
                            ))}
                          </div>
                        </div>
                      )}

                      {message.response?.risk_assessment && (
                        <div>
                          <span className="font-medium text-foreground">Risk assessment:</span>
                          <div className="ml-2 text-xs text-muted-foreground whitespace-pre-wrap">
                            {message.response.risk_assessment}
                          </div>
                        </div>
                      )}
                    </div>
                  </CollapsibleContent>
                </Collapsible>
              </div>
            )
          }
        </div>

        <div className={`text-xs text-muted-foreground mt-2 ${isUser ? 'text-right' : 'text-left'}`}>
          {formatTime(message.timestamp)}
        </div>
      </div>

      {/* PDF Viewer Portal */}
      {pdfState.isOpen && pdfState.pdfUrl && (
        <PdfViewer
          fileUrl={pdfState.pdfUrl || ''}
          initialPage={pdfState.pageNumber || 1}
          highlightText={pdfState.highlightText || undefined}
          title={pdfState.title || undefined}
          onClose={closePdf}
        />
      )}
    </div>
  )
}
