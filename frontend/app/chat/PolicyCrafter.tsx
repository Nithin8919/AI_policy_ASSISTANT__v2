'use client'

import { useState, useEffect, useRef } from 'react'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { modelService } from '@/lib/modelService'
import { AIModel } from '@/lib/models'
import { queryModelDirect } from '@/lib/api'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuRadioGroup, DropdownMenuRadioItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { ArrowLeft, Sparkles, Loader2, FileText, Zap, Shield, Users, MessageSquare, Maximize2, Minimize2, ChevronLeft, ChevronRight, ArrowLeftRight, ZoomIn, ZoomOut, Check, RotateCcw, Download, Printer, Maximize, File, Book, GraduationCap, Plus, Minus, Trash2, Bot, Edit3, AtSign, Globe, Image as ImageIcon, CornerUpRight } from 'lucide-react'

interface PolicyCrafterProps {
  onReturnToChat: () => void
}
type LayoutState = 'default' | 'focus' | 'deep-assist' | 'full-agent'
type PolicyTemplate = 'none' | 'indian-education' | 'gitam-education'

interface Page {
  id: string
  title: string
  content: string
  template?: PolicyTemplate
  isEdited?: boolean
  customContent?: string
  editableFields?: {
    title?: string
    subtitle?: string
    version?: string
    sections?: Array<{
      id: string
      sectionTitle: string
      content: string
    }>
  }
}

type ChatAction = {
  op: 'add' | 'update' | 'delete'
  target: 'section' | 'page'
  pageId?: string
  sectionId?: string
  title?: string
  content?: string
  index?: number
}

type ChatEntry = {
  id: string
  role: 'user' | 'assistant'
  question?: string
  understood?: string
  actions?: ChatAction[]
  applied?: string[]
  status?: 'pending' | 'accepted' | 'rejected'
  raw?: string
  timestamp: number
}

export function PolicyCrafter({ onReturnToChat }: PolicyCrafterProps) {
  // Helper function to get template content
  const getPageTemplateContent = (template: PolicyTemplate) => {
    switch (template) {
      case 'indian-education':
        return {
          title: 'National Education Policy 2020',
          subtitle: 'Transforming India\'s Education System',
          version: 'Version 1.0 | Effective Date: 2024',
          content: [
            {
              section: 'Introduction',
              text: 'The National Education Policy (NEP) 2020 aims to transform the Indian education system by providing equitable and inclusive education to all. It emphasizes holistic development, critical thinking, and creativity among learners.'
            },
            {
              section: 'Key Objectives',
              text: '• Access: Ensure universal access to quality education at all levels\n• Equity: Bridge the gap between different socio-economic groups\n• Quality: Enhance the quality of education through curriculum reforms\n• Affordability: Provide affordable education to all sections of society\n• Accountability: Establish a robust framework for monitoring and evaluation'
            },
            {
              section: 'Structural Changes',
              text: '• School Education: Adopt a new curricular structure of 5+3+3+4, corresponding to ages 3–8, 8–11, 11–14, and 14–18 years\n• Higher Education: Introduce a multidisciplinary approach with flexible curricula, multiple entry and exit points, and a credit-based system'
            },
            {
              section: 'Language Policy',
              text: 'Implement the three-language formula, promoting multilingualism and national unity. The medium of instruction until at least Grade 5, and preferably till Grade 8 and beyond, will be the home language/mother tongue/local language/regional language.'
            },
            {
              section: 'Technology Integration',
              text: 'Leverage technology for enhancing learning experiences, teacher training, and educational planning and management.'
            }
          ]
        }
      case 'gitam-education':
        return {
          title: 'GITAM Education Policy Framework',
          subtitle: 'Holistic Education for Global Excellence',
          version: 'Version 1.0 | Effective Date: 2024',
          content: [
            {
              section: 'Introduction',
              text: 'GITAM is committed to providing a holistic education that fosters intellectual growth, ethical values, and social responsibility. Our education policy aligns with the National Education Policy 2020 and aims to equip students with the skills and knowledge required for the 21st century.'
            },
            {
              section: 'Vision',
              text: 'To impart futuristic and comprehensive education of global standards with a high sense of discipline and social relevance in a serene and invigorating environment.'
            },
            {
              section: 'Mission',
              text: '• Academic Excellence: Offer a wide range of programs that lead to the development of competent professionals\n• Research and Innovation: Promote research and innovation through collaboration with industry and academia\n• Community Engagement: Engage with the community through outreach programs and social initiatives'
            },
            {
              section: 'Core Values',
              text: '• Integrity: Upholding the highest ethical standards in all endeavors\n• Excellence: Striving for excellence in teaching, research, and service\n• Inclusivity: Fostering an inclusive environment that respects diversity'
            },
            {
              section: 'Educational Approach',
              text: '• Liberal Education: Offers over 600 major-minor combinations, allowing students to tailor their education\n• Integrated Programs: Introduces Integrated Teacher Education Programs aligned with NEP 2020\n• Technology Integration: Utilize digital tools and platforms to enhance the teaching-learning experience'
            }
          ]
        }
      default:
        return {
          title: 'Policy Document',
          subtitle: 'GITAM Education Policy Framework',
          version: 'Version 1.0 | Effective Date: 2024',
          content: []
        }
    }
  }

  // Helper function to initialize editable fields for templates
  const initializeEditableFields = (template: PolicyTemplate) => {
    const templateContent = getPageTemplateContent(template)

    if (template === 'none') {
      return {
        title: 'Policy Document',
        subtitle: 'Click to edit subtitle',
        version: 'Version 1.0 | Effective Date: 2024',
        sections: []
      }
    }

    return {
      title: templateContent.title,
      subtitle: templateContent.subtitle,
      version: templateContent.version,
      sections: templateContent.content.map((section: any, index: number) => ({
        id: `section-${index}`,
        sectionTitle: section.section,
        content: section.text
      }))
    }
  }

  const [isLoading, setIsLoading] = useState(true)
  const [layoutState, setLayoutState] = useState<LayoutState>('default')
  const [isSwapped, setIsSwapped] = useState(false)
  const [zoomLevel, setZoomLevel] = useState(100)
  const [rotation, setRotation] = useState(0)
  const [currentTemplate, setCurrentTemplate] = useState<PolicyTemplate>('none')
  const [showTemplatePopup, setShowTemplatePopup] = useState(false)
  const [pages, setPages] = useState<Page[]>([
    {
      id: '1',
      title: 'Page 1',
      content: '',
      template: 'none',
      editableFields: initializeEditableFields('none')
    }
  ])
  const [currentPageIndex, setCurrentPageIndex] = useState(0)
  const [zoomTextColor, setZoomTextColor] = useState('text-white')
  const [pageTextColor, setPageTextColor] = useState('text-gray-900')
  const [micaBackground, setMicaBackground] = useState('bg-gradient-to-br from-white/20 via-white/10 to-white/5')
  const [isAIGenerating, setIsAIGenerating] = useState(false)
  const a4PanelRef = useRef<HTMLDivElement>(null)
  const [chatMode, setChatMode] = useState<'agent' | 'brainstorm' | 'memory'>('agent')
  const [availableModels, setAvailableModels] = useState<AIModel[]>([])
  const [selectedModelId, setSelectedModelId] = useState<string>('')
  const chatInputRef = useRef<HTMLTextAreaElement>(null)
  const [usagePercent, setUsagePercent] = useState<number>(0)
  const MAX_CHARS_PER_PAGE = 800 // Reduced from 1200 to prevent overflow
  const [messages, setMessages] = useState<ChatEntry[]>([])

  const optimizeMarkdown = (input: string): string => {
    if (!input) return ''
    let out = input.replace(/[ \t]+$/gm, '') // trim line-end spaces
    out = out.replace(/\n{3,}/g, '\n\n') // collapse blank lines
    out = out.replace(/^\s*[•·]\s+/gm, '- ') // normalize bullets
    return out.trim()
  }

  const splitIntoPageChunks = (text: string, max: number): string[] => {
    if (text.length <= max) return [text]

    // Split by logical breaks (paragraphs, then sentences)
    const paragraphs = text.split(/\n\n+/)
    const chunks: string[] = []
    let currentChunk = ''

    for (const para of paragraphs) {
      if ((currentChunk.length + para.length + 2) <= max) {
        currentChunk += (currentChunk ? '\n\n' : '') + para
      } else {
        // Push current chunk if it exists
        if (currentChunk) {
          chunks.push(currentChunk)
          currentChunk = ''
        }

        // If paragraph itself is huge, split it hard
        if (para.length > max) {
          let remaining = para
          while (remaining.length > max) {
            // Try to split at a period or space near the max limit
            let splitIndex = remaining.lastIndexOf('.', max)
            if (splitIndex === -1 || splitIndex < max * 0.7) {
              splitIndex = remaining.lastIndexOf(' ', max)
            }
            if (splitIndex === -1) splitIndex = max // Forced split

            chunks.push(remaining.slice(0, splitIndex + 1))
            remaining = remaining.slice(splitIndex + 1).trim()
          }
          currentChunk = remaining
        } else {
          currentChunk = para
        }
      }
    }
    if (currentChunk) chunks.push(currentChunk)

    return chunks
  }

  /* Helper function to apply CRUD actions */


  const applyCrudActions = (actions: ChatAction[]): string[] => {
    const executed: string[] = []

    // Sort actions to handle page creation first if needed (basic logic)
    const sorted = [...actions].sort((a, b) => {
      if (a.target === 'page' && b.target !== 'page') return -1
      return 0
    })

    sorted.forEach(action => {
      try {
        if (action.target === 'page') {
          if (action.op === 'add') {
            const newPageId = `page-${Date.now()}-${Math.random()}`
            const newPage: Page = {
              id: newPageId,
              title: action.title || 'New Policy Page',
              content: '',
              template: 'none',
              editableFields: {
                title: action.title || 'New Policy Page',
                sections: []
              }
            }
            setPages(prev => [...prev, newPage])
            executed.push(`Created new page: "${newPage.title}"`)
          } else if (action.op === 'delete' && action.pageId) {
            setPages(prev => prev.filter(p => p.id !== action.pageId))
            executed.push(`Deleted page ID: ${action.pageId}`)
          }
        } else if (action.target === 'section') {
          if (action.op === 'add') {
            // Add to current page if no pageId provided
            const targetPageId = action.pageId || pages[currentPageIndex].id
            const newSectionId = `sec-${Date.now()}-${Math.random()}`
            setPages(prev => prev.map(p => {
              if (p.id === targetPageId) {
                const currentSections = p.editableFields?.sections || []
                return {
                  ...p,
                  isEdited: true,
                  editableFields: {
                    ...p.editableFields,
                    sections: [
                      ...currentSections,
                      {
                        id: newSectionId,
                        sectionTitle: action.title || 'New Section',
                        content: optimizeMarkdown(action.content || '')
                      }
                    ]
                  }
                }
              }
              return p
            }))
            executed.push(`Added section: "${action.title || 'New Section'}"`)
            // Trigger pagination check after minimal delay
            setTimeout(() => paginateSectionContent(targetPageId, newSectionId), 100)

          } else if (action.op === 'update' && action.pageId && action.sectionId && action.content) {
            updateSectionContent(action.pageId, action.sectionId, action.content)
            executed.push(`Updated section: "${action.title || 'Section'}"`)
            setTimeout(() => paginateSectionContent(action.pageId!, action.sectionId!), 100)

          } else if (action.op === 'delete' && action.pageId && action.sectionId) {
            setPages(prev => prev.map(p => {
              if (p.id === action.pageId) {
                return {
                  ...p,
                  isEdited: true,
                  editableFields: {
                    ...p.editableFields,
                    sections: (p.editableFields?.sections || []).filter(s => s.id !== action.sectionId)
                  }
                }
              }
              return p
            }))
            executed.push(`Deleted section from page ${action.pageId}`)
          }
        }
      } catch (err) {
        console.error('Failed to execute action:', action, err)
      }
    })
    return executed
  }

  const handleSend = () => {
    const input = chatInputRef.current
    if (input && input.value.trim() && pages.length > 0) {
      const questionText = input.value.trim()
      const userEntry: ChatEntry = {
        id: `m-${Date.now()}`,
        role: 'user',
        question: questionText,
        timestamp: Date.now()
      }
      setMessages(prev => [...prev, userEntry])
      input.value = ''
      runUnderstandingAndApply(questionText)
    }
  }

  const paginateSectionContent = (pageId: string, sectionId: string) => {
    setPages(prev => {
      const pagesCopy = [...prev]
      const pageIndex = pagesCopy.findIndex(p => p.id === pageId)
      if (pageIndex < 0) return prev
      const page = pagesCopy[pageIndex]
      if (!page.editableFields?.sections) return prev
      const section = page.editableFields.sections.find(s => s.id === sectionId)
      if (!section) return prev

      const optimized = optimizeMarkdown(section.content || '')

      // Fallback logic mostly relies on character count now for stability
      const chunks = splitIntoPageChunks(optimized, MAX_CHARS_PER_PAGE)

      // Update current section with first chunk
      section.content = chunks[0] || ''

      // Create new pages for subsequent chunks
      if (chunks.length > 1) {
        // Remove ANY existing continuation pages for this section first to avoid duplicates if re-running
        // Note: This logic is simple; sophisticated approach would track related pages. 
        // For now, we just insert new pages.
      }

      for (let i = 1; i < chunks.length; i++) {
        const newPage: Page = {
          id: `${Date.now()}-${i}-${Math.random().toString(36).slice(2, 6)}`,
          title: (page.editableFields?.title || page.title), // Keep original title
          content: '',
          template: page.template || 'none',
          editableFields: {
            title: (page.editableFields?.title || page.title),
            subtitle: page.editableFields?.subtitle,
            version: page.editableFields?.version,
            sections: [
              {
                id: `section-${Date.now()}-${i}`,
                sectionTitle: (section.sectionTitle || 'Section') + ` (cont.)`,
                content: chunks[i]
              }
            ]
          }
        }
        pagesCopy.splice(pageIndex + i, 0, newPage)
      }
      return pagesCopy
    })
  }
  const focusPageById = (pageId?: string) => {
    if (!pageId) return
    setPages(prev => {
      const idx = prev.findIndex(p => p.id === pageId)
      if (idx >= 0) {
        setCurrentPageIndex(idx)
      }
      return prev
    })
  }
  /* New Typings for Review Workflow */
  type ChatAction = {
    op: 'add' | 'update' | 'delete'
    target: 'section' | 'page'
    pageId?: string
    sectionId?: string
    title?: string
    content?: string
    index?: number
  }

  type ChatEntry = {
    id: string
    role: 'user' | 'assistant'
    question?: string
    understood?: string
    actions?: ChatAction[]
    applied?: string[]
    status?: 'pending' | 'accepted' | 'rejected' // Added status
    raw?: string
    timestamp: number
  }

  const handleApplyActions = (messageId: string, actions: ChatAction[]) => {
    const appliedSummaries = applyCrudActions(actions)
    setMessages(prev => prev.map(msg =>
      msg.id === messageId
        ? { ...msg, status: 'accepted', applied: appliedSummaries }
        : msg
    ))
  }

  const handleDiscardActions = (messageId: string) => {
    setMessages(prev => prev.map(msg =>
      msg.id === messageId
        ? { ...msg, status: 'rejected' }
        : msg
    ))
  }

  const runUnderstandingAndApply = async (prompt: string) => {
    setIsAIGenerating(true)
    try {
      // NOTE: We do NOT send the system instruction here anymore.
      // The backend handles the prompt template for 'policy_draft' mode.

      console.log('🔵 PolicyCrafter: Sending query to API...')
      const { answer } = await queryModelDirect({
        query: prompt, // Send ONLY the user prompt
        mode: 'policy_draft'
      })
      console.log('✅ PolicyCrafter: Got response from API')

      const parsed = safeParseJSON(answer)
      const understanding: string = parsed?.understanding || 'I have processed your request.'
      const actions: ChatAction[] = Array.isArray(parsed?.actions) ? parsed.actions : []

      // If no valid actions returned, maybe it was a general question or failed generation
      if (actions.length === 0) {
        const assistantEntry: ChatEntry = {
          id: `a-${Date.now()}`,
          role: 'assistant',
          understood: understanding,
          actions: [],
          applied: [],
          status: 'accepted', // No actions to review
          raw: answer,
          timestamp: Date.now()
        }
        setMessages(prev => [...prev, assistantEntry])
        return
      }

      // Create a PENDING entry for user review
      const assistantEntry: ChatEntry = {
        id: `a-${Date.now()}`,
        role: 'assistant',
        understood: understanding,
        actions,
        applied: [],
        status: 'pending', // Wait for user approval
        raw: answer,
        timestamp: Date.now()
      }
      setMessages(prev => [...prev, assistantEntry])

    } catch (e) {
      console.error('Understanding/apply failed:', e)
      const assistantEntry: ChatEntry = {
        id: `a-${Date.now()}`,
        role: 'assistant',
        understood: 'Failed to process your request.',
        applied: [],
        status: 'rejected',
        raw: String(e),
        timestamp: Date.now()
      }
      setMessages(prev => [...prev, assistantEntry])
    } finally {
      setIsAIGenerating(false)
    }
  }

  const safeParseJSON = (text: string): any => {
    try {
      return JSON.parse(text)
    } catch { }
    try {
      const m = text.match(/```json[\s\S]*?```/i)
      if (m) {
        const inner = m[0].replace(/```json|```/g, '')
        return JSON.parse(inner)
      }
    } catch { }
    try {
      const start = text.indexOf('{')
      const end = text.lastIndexOf('}')
      if (start >= 0 && end > start) {
        return JSON.parse(text.slice(start, end + 1))
      }
    } catch { }
    return null
  }



  useEffect(() => {
    // Simulate loading time
    const timer = setTimeout(() => {
      setIsLoading(false)
    }, 2000)

    return () => clearTimeout(timer)
  }, [])

  // Click outside handler for template popup
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (showTemplatePopup) {
        const target = event.target as Element
        if (!target.closest('[data-template-popup]')) {
          setShowTemplatePopup(false)
        }
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [showTemplatePopup])

  // Dynamic text color detection based on background
  useEffect(() => {
    const detectBackgroundColor = () => {
      if (a4PanelRef.current) {
        const backgroundColor = getBackgroundColor(a4PanelRef.current)
        const textColor = getTextColorForBackground(backgroundColor)
        setZoomTextColor(textColor)
        setPageTextColor(textColor)
      }

      // Update mica background based on theme
      const adaptiveBackground = getAdaptiveMicaBackground()
      setMicaBackground(adaptiveBackground)
    }

    // Initial detection
    detectBackgroundColor()

    // Set up observer for theme changes
    const observer = new MutationObserver(detectBackgroundColor)
    if (a4PanelRef.current) {
      observer.observe(document.body, {
        attributes: true,
        attributeFilter: ['class', 'data-theme']
      })
    }

    // Listen for theme changes
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    mediaQuery.addEventListener('change', detectBackgroundColor)

    return () => {
      observer.disconnect()
      mediaQuery.removeEventListener('change', detectBackgroundColor)
    }
  }, [layoutState, isSwapped])

  // Layout state functions - A4 gets more space regardless of position
  const getLayoutClasses = () => {
    switch (layoutState) {
      case 'default':
        return {
          left: 'w-[25%]',    // Agent gets 25%
          right: 'w-[75%]'    // A4 gets 75%
        }
      case 'focus':
        return {
          left: 'w-[5%]',     // Agent collapsed
          right: 'w-[95%]'    // A4 gets almost full space
        }
      case 'deep-assist':
        return {
          left: 'w-[35%]',    // Agent gets more space for collaboration
          right: 'w-[65%]'    // A4 still gets majority
        }
      case 'full-agent':
        return {
          left: 'w-[50%]',    // Agent gets equal space
          right: 'w-[50%]'    // A4 gets equal space
        }
      default:
        return {
          left: 'w-[25%]',
          right: 'w-[75%]'
        }
    }
  }

  const layoutClasses = getLayoutClasses()

  // Zoom control functions
  const handleZoomIn = () => {
    setZoomLevel(prev => Math.min(prev + 25, 300))
  }

  const handleZoomOut = () => {
    setZoomLevel(prev => Math.max(prev - 25, 50))
  }

  const handleZoomReset = () => {
    setZoomLevel(100)
  }

  const handleFitToWidth = () => {
    setZoomLevel(85) // Approximate fit-to-width for A4
  }

  const handleRotate = () => {
    setRotation(prev => (prev + 90) % 360)
  }

  const handleDownload = () => {
    // TODO: Implement PDF download functionality
    console.log('Download PDF')
  }

  const handlePrint = () => {
    // TODO: Implement print functionality
    window.print()
  }

  // Get current template from pages
  const getCurrentTemplateFromPages = () => {
    if (pages.length === 0) return 'none'
    const firstPageTemplate = pages[0].template
    // Check if all pages have the same template
    const allSameTemplate = pages.every(page => page.template === firstPageTemplate)
    return allSameTemplate ? firstPageTemplate : 'mixed'
  }

  // Dynamic text color based on background brightness
  const getTextColorForBackground = (backgroundColor: string): string => {
    // Convert RGB to brightness
    const rgbMatch = backgroundColor.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/)
    if (rgbMatch) {
      const r = parseInt(rgbMatch[1])
      const g = parseInt(rgbMatch[2])
      const b = parseInt(rgbMatch[3])

      // Calculate brightness using luminance formula
      const brightness = (r * 299 + g * 587 + b * 114) / 1000

      // Return appropriate text color based on brightness
      return brightness > 128 ? 'text-gray-900' : 'text-white'
    }

    // Fallback for other color formats
    return 'text-white'
  }

  // Get adaptive mica background based on theme
  const getAdaptiveMicaBackground = (): string => {
    // Check if dark theme is active
    const isDarkTheme = document.documentElement.classList.contains('dark') ||
      window.matchMedia('(prefers-color-scheme: dark)').matches

    if (isDarkTheme) {
      return 'bg-gradient-to-br from-gray-900/20 via-gray-800/10 to-gray-900/5'
    } else {
      return 'bg-gradient-to-br from-white/20 via-white/10 to-white/5'
    }
  }

  // Get computed background color from element
  const getBackgroundColor = (element: HTMLElement): string => {
    const computedStyle = window.getComputedStyle(element)
    return computedStyle.backgroundColor || 'rgb(255, 255, 255)'
  }

  // Template handling functions
  const handleTemplateLoad = (template: PolicyTemplate) => {
    setCurrentTemplate(template)
    // Apply template to all pages with editable fields
    setPages(prev => prev.map(page => ({
      ...page,
      template,
      editableFields: initializeEditableFields(template)
    })))
    setShowTemplatePopup(false)
  }

  const handleTemplateLoadToNewPage = (template: PolicyTemplate) => {
    const newPage: Page = {
      id: Date.now().toString(),
      title: `Page ${pages.length + 1}`,
      content: '',
      template,
      editableFields: initializeEditableFields(template)
    }
    setPages(prev => [...prev, newPage])
    setShowTemplatePopup(false)
  }

  // Page management functions
  const addPage = () => {
    const newPage: Page = {
      id: Date.now().toString(),
      title: `Page ${pages.length + 1}`,
      content: '',
      template: 'none',
      editableFields: initializeEditableFields('none')
    }
    setPages(prev => [...prev, newPage])
    setCurrentPageIndex(pages.length)
  }

  const removePage = (pageIndex: number) => {
    if (pages.length <= 1) return // Don't remove the last page

    setPages(prev => prev.filter((_, index) => index !== pageIndex))

    // Adjust current page index if needed
    if (currentPageIndex >= pageIndex) {
      setCurrentPageIndex(Math.max(0, currentPageIndex - 1))
    }
  }

  // Direct editing functions
  const updatePageField = (pageId: string, fieldType: 'title' | 'subtitle' | 'version', newValue: string) => {
    setPages(prev => prev.map(page => {
      if (page.id !== pageId) return page

      const updatedPage = { ...page, isEdited: true }

      if (!updatedPage.editableFields) {
        updatedPage.editableFields = {}
      }

      switch (fieldType) {
        case 'title':
          updatedPage.editableFields.title = newValue
          break
        case 'subtitle':
          updatedPage.editableFields.subtitle = newValue
          break
        case 'version':
          updatedPage.editableFields.version = newValue
          break
      }

      return updatedPage
    }))
  }

  const updateSectionContent = (pageId: string, sectionId: string, newContent: string) => {
    setPages(prev => prev.map(page => {
      if (page.id !== pageId) return page

      const updatedPage = { ...page, isEdited: true }

      if (!updatedPage.editableFields) {
        updatedPage.editableFields = { sections: [] }
      }

      if (updatedPage.editableFields.sections) {
        updatedPage.editableFields.sections = updatedPage.editableFields.sections.map(section =>
          section.id === sectionId ? { ...section, content: optimizeMarkdown(newContent) } : section
        )
      }

      return updatedPage
    }))
    // paginate after state commit
    setTimeout(() => paginateSectionContent(pageId, sectionId), 0)
  }

  const generateWithAI = async (pageId: string, fieldType: 'title' | 'subtitle' | 'version' | 'section', prompt: string, sectionId?: string) => {
    setIsAIGenerating(true)
    try {
      // Simulate AI generation - replace with actual API call
      await new Promise(resolve => setTimeout(resolve, 2000))

      let aiGeneratedContent = ''
      switch (fieldType) {
        case 'title':
          aiGeneratedContent = `AI Generated Policy Title: ${prompt}`
          break
        case 'subtitle':
          aiGeneratedContent = `AI Generated Subtitle: ${prompt}`
          break
        case 'version':
          aiGeneratedContent = `Version 2.0 | Effective Date: ${new Date().getFullYear()}`
          break
        case 'section':
          aiGeneratedContent = `AI Generated Section Content:\n\n${prompt}\n\nThis section has been enhanced with AI-generated content based on your requirements. The content includes relevant policy guidelines, implementation strategies, and compliance considerations.`
          break
      }

      setPages(prev => prev.map(page => {
        if (page.id !== pageId) return page

        const updatedPage = { ...page, isEdited: true }

        if (!updatedPage.editableFields) {
          updatedPage.editableFields = {}
        }

        switch (fieldType) {
          case 'title':
            updatedPage.editableFields.title = aiGeneratedContent
            break
          case 'subtitle':
            updatedPage.editableFields.subtitle = aiGeneratedContent
            break
          case 'version':
            updatedPage.editableFields.version = aiGeneratedContent
            break
          case 'section':
            if (sectionId && updatedPage.editableFields.sections) {
              updatedPage.editableFields.sections = updatedPage.editableFields.sections.map(section =>
                section.id === sectionId ? { ...section, content: aiGeneratedContent } : section
              )
            }
            break
        }

        return updatedPage
      }))
    } catch (error) {
      console.error('AI generation failed:', error)
    } finally {
      setIsAIGenerating(false)
    }
  }

  // Calculate zoom overlay position based on layout state
  const getZoomPosition = () => {
    const layoutClasses = getLayoutClasses()

    // Extract width percentages from layout classes
    const getWidthPercentage = (widthClass: string) => {
      switch (widthClass) {
        case 'w-[25%]': return 25
        case 'w-[5%]': return 5
        case 'w-[35%]': return 35
        case 'w-[50%]': return 50
        case 'w-[75%]': return 75
        case 'w-[95%]': return 95
        case 'w-[65%]': return 65
        default: return 25
      }
    }

    const leftWidth = getWidthPercentage(layoutClasses.left)

    if (isSwapped) {
      // When swapped, A4 is on the left
      return `calc(100% - ${leftWidth}% + 1.5rem)`
    } else {
      // Normal layout, A4 is on the right
      return `1.5rem`
    }
  }

  const renderPage = (page: Page, pageIndex: number) => {
    const templateContent = getPageTemplateContent(page.template || 'none')

    return (
      <div
        key={page.id}
        className="bg-white shadow-lg rounded-lg border transition-transform duration-200 ease-in-out relative group"
        style={{
          width: '210mm',
          height: '297mm',
          maxWidth: '100%',
          aspectRatio: '210/297',
          padding: '20mm',
          transform: `scale(${zoomLevel / 100}) rotate(${rotation}deg)`,
          transformOrigin: 'center'
        }}
        data-page-id={page.id}
      >
        {/* Delete Button - Top Right */}
        {pages.length > 1 && (
          <Button
            variant="destructive"
            size="sm"
            onClick={() => removePage(pageIndex)}
            className="absolute -top-2 -right-2 w-8 h-8 p-0 rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-200 z-20"
            title={`Delete Page ${pageIndex + 1}`}
          >
            <Trash2 className="w-4 h-4" />
          </Button>
        )}
        <div className="h-full flex flex-col">
          {/* Document Content */}
          <div className={`flex-1 space-y-4 ${pageTextColor} text-sm leading-relaxed`}>
            {/* Editable Title */}
            <div className="text-center border-b pb-4 mb-6">
              <div className="group cursor-pointer hover:bg-blue-50/50 rounded-lg p-2 -m-2 transition-colors">
                <h1
                  className="text-xl font-bold text-gray-900 group-hover:text-blue-600 transition-colors outline-none focus:outline-none focus:ring-0"
                  contentEditable
                  suppressContentEditableWarning={true}
                  onBlur={(e) => {
                    const newTitle = e.currentTarget.textContent || ''
                    if (newTitle !== (page.editableFields?.title || templateContent.title)) {
                      updatePageField(page.id, 'title', newTitle)
                    }
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault()
                      e.currentTarget.blur()
                    }
                  }}
                >
                  {page.editableFields?.title || templateContent.title}
                </h1>
              </div>

              {/* Editable Subtitle */}
              <div className="group cursor-pointer hover:bg-blue-50/50 rounded-lg p-2 -m-2 transition-colors">
                <p
                  className="text-xs text-gray-600 mt-1 group-hover:text-blue-600 transition-colors outline-none focus:outline-none focus:ring-0"
                  contentEditable
                  suppressContentEditableWarning={true}
                  onBlur={(e) => {
                    const newSubtitle = e.currentTarget.textContent || ''
                    if (newSubtitle !== (page.editableFields?.subtitle || templateContent.subtitle)) {
                      updatePageField(page.id, 'subtitle', newSubtitle)
                    }
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault()
                      e.currentTarget.blur()
                    }
                  }}
                >
                  {page.editableFields?.subtitle || templateContent.subtitle}
                </p>
              </div>

              {/* Editable Version */}
              <div className="group cursor-pointer hover:bg-blue-50/50 rounded-lg p-2 -m-2 transition-colors">
                <p
                  className="text-xs text-gray-500 mt-1 group-hover:text-blue-600 transition-colors outline-none focus:outline-none focus:ring-0"
                  contentEditable
                  suppressContentEditableWarning={true}
                  onBlur={(e) => {
                    const newVersion = e.currentTarget.textContent || ''
                    if (newVersion !== (page.editableFields?.version || templateContent.version)) {
                      updatePageField(page.id, 'version', newVersion)
                    }
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault()
                      e.currentTarget.blur()
                    }
                  }}
                >
                  {page.editableFields?.version || templateContent.version}
                </p>
              </div>
            </div>

            {/* Editable Content Sections */}
            <div className="space-y-4">
              {page.editableFields?.sections && page.editableFields.sections.length > 0 ? (
                page.editableFields.sections.map((section, index) => (
                  <div key={section.id} className="space-y-2">
                    <h3 className="font-semibold text-gray-900 text-base border-b border-gray-200 pb-1">
                      {section.sectionTitle}
                    </h3>
                    <div
                      className="group rounded-lg p-3 -m-3"
                    >
                      <div
                        className="text-gray-700 whitespace-pre-line outline-none focus:outline-none focus:ring-0"
                        contentEditable
                        suppressContentEditableWarning={true}
                        onKeyDown={(e) => {
                          const el = e.currentTarget as HTMLElement
                          if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                            e.preventDefault()
                            // Insert new section after
                            const newSectionId = `section-${Date.now()}`
                            setPages(prev => prev.map(p => {
                              if (p.id === page.id) {
                                const updated = { ...p, isEdited: true }
                                if (!updated.editableFields) updated.editableFields = { sections: [] }
                                if (!updated.editableFields.sections) updated.editableFields.sections = []
                                const pos = updated.editableFields.sections.findIndex(s => s.id === section.id)
                                updated.editableFields.sections = [
                                  ...updated.editableFields.sections.slice(0, pos + 1),
                                  { id: newSectionId, sectionTitle: 'New Section', content: '' },
                                  ...updated.editableFields.sections.slice(pos + 1)
                                ]
                                return updated
                              }
                              return p
                            }))
                          }
                          if (e.key === 'Delete' && e.shiftKey) {
                            const text = el.textContent || ''
                            if (!text.trim()) {
                              e.preventDefault()
                              setPages(prev => prev.map(p => {
                                if (p.id === page.id) {
                                  const updated = { ...p, isEdited: true }
                                  if (!updated.editableFields?.sections) return p
                                  updated.editableFields.sections = updated.editableFields.sections.filter(s => s.id !== section.id)
                                  return updated
                                }
                                return p
                              }))
                            }
                          }
                        }}
                        onBlur={(e) => {
                          const newContent = e.currentTarget.textContent || ''
                          if (newContent !== section.content) {
                            updateSectionContent(page.id, section.id, newContent)
                          }
                        }}
                      >
                        {section.content}
                      </div>
                    </div>
                  </div>
                ))
              ) : page.template === 'none' ? (
                // Placeholder content for blank template with hover overlay
                <div className="relative group">
                  {/* Hover overlay for skeleton content */}
                  <div
                    className="absolute inset-0 bg-blue-50/80 opacity-0 group-hover:opacity-100 transition-opacity duration-200 rounded-lg flex items-center justify-center cursor-pointer z-10"
                    onClick={() => {
                      // Create a new section for blank templates
                      const newSectionId = `section-${Date.now()}`
                      setPages(prev => prev.map(p => {
                        if (p.id === page.id) {
                          const updatedPage = { ...p, isEdited: true }
                          if (!updatedPage.editableFields) {
                            updatedPage.editableFields = { sections: [] }
                          }
                          if (!updatedPage.editableFields.sections) {
                            updatedPage.editableFields.sections = []
                          }
                          updatedPage.editableFields.sections.push({
                            id: newSectionId,
                            sectionTitle: 'New Section',
                            content: ''
                          })
                          return updatedPage
                        }
                        return p
                      }))
                    }}
                  >
                    <div className="bg-white rounded-lg shadow-lg p-4 flex items-center gap-2 text-sm font-medium text-blue-600">
                      <Edit3 className="w-4 h-4" />
                      Start Editing
                    </div>
                  </div>

                  {/* Skeleton content */}
                  <div className="space-y-4">
                    <div className="h-3 bg-gray-200 rounded w-3/4"></div>
                    <div className="h-3 bg-gray-200 rounded w-full"></div>
                    <div className="h-3 bg-gray-200 rounded w-5/6"></div>
                    <div className="h-3 bg-gray-200 rounded w-2/3"></div>

                    <div className="mt-6 space-y-2">
                      <div className="h-3 bg-gray-200 rounded w-1/2"></div>
                      <div className="h-3 bg-gray-200 rounded w-full"></div>
                      <div className="h-3 bg-gray-200 rounded w-4/5"></div>
                      <div className="h-3 bg-gray-200 rounded w-3/4"></div>
                    </div>

                    <div className="mt-6 space-y-2">
                      <div className="h-3 bg-gray-200 rounded w-2/3"></div>
                      <div className="h-3 bg-gray-200 rounded w-full"></div>
                      <div className="h-3 bg-gray-200 rounded w-5/6"></div>
                    </div>

                    <div className="mt-6 space-y-2">
                      <div className="h-3 bg-gray-200 rounded w-1/3"></div>
                      <div className="h-3 bg-gray-200 rounded w-full"></div>
                      <div className="h-3 bg-gray-200 rounded w-4/5"></div>
                      <div className="h-3 bg-gray-200 rounded w-2/3"></div>
                    </div>
                  </div>
                </div>
              ) : (
                // Fallback to template content if editableFields is not properly initialized
                templateContent.content.map((section, index) => (
                  <div key={index} className="space-y-2">
                    <h3 className="font-semibold text-gray-900 text-base border-b border-gray-200 pb-1">
                      {section.section}
                    </h3>
                    <div className="text-gray-700 whitespace-pre-line">
                      {section.text}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Document Footer */}
          <div className="mt-6 pt-4 border-t text-xs text-gray-500 text-center">
            <p>Page {pageIndex + 1} of {pages.length} | Document ID: POL-2024-001</p>
          </div>
        </div>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="fixed inset-0 flex flex-col items-center justify-center bg-gradient-to-br from-background to-muted/20 z-50">
        <div className="text-center space-y-6 max-w-md mx-auto px-6">
          {/* Loading Animation */}
          <div className="relative">
            <div className="w-16 h-16 mx-auto mb-4 relative">
              <div className="absolute inset-0 rounded-full border-4 border-primary/20"></div>
              <div className="absolute inset-0 rounded-full border-4 border-primary border-t-transparent animate-spin"></div>
              <div className="absolute inset-2 rounded-full bg-primary/10 flex items-center justify-center">
                <Sparkles className="w-6 h-6 text-primary animate-pulse" />
              </div>
            </div>
          </div>

          {/* Loading Text */}
          <div className="space-y-2">
            <h2 className="text-xl font-semibold text-foreground">
              Initializing Policy Crafter
            </h2>
            <p className="text-sm text-muted-foreground">
              Preparing advanced policy analysis tools...
            </p>
          </div>

          {/* Loading Steps */}
          <div className="space-y-3 text-left">
            <div className="flex items-center gap-3 text-sm">
              <Loader2 className="w-4 h-4 text-primary animate-spin" />
              <span className="text-muted-foreground">Loading policy templates</span>
            </div>
            <div className="flex items-center gap-3 text-sm">
              <Loader2 className="w-4 h-4 text-primary animate-spin" />
              <span className="text-muted-foreground">Initializing compliance engine</span>
            </div>
            <div className="flex items-center gap-3 text-sm">
              <Loader2 className="w-4 h-4 text-primary animate-spin" />
              <span className="text-muted-foreground">Setting up AI analysis tools</span>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 bg-gradient-to-br from-background to-muted/20 z-50 overflow-hidden">

      {/* Dual Panel Layout */}
      <div className={`h-full flex transition-all duration-300 ease-in-out ${isSwapped ? 'flex-row-reverse' : 'flex-row'}`}>
        {/* Agent Chatbot Panel */}
        <div className={`${layoutClasses.left} transition-all duration-300 ease-in-out bg-muted/20 ${isSwapped ? 'border-l' : 'border-r'}`}>
          {layoutState === 'focus' ? (
            /* Collapsed Agent - Just Icon */
            <div className="h-full flex items-center justify-center">
              <Button
                variant="ghost"
                size="lg"
                onClick={() => setLayoutState('default')}
                className="rounded-full w-12 h-12 bg-primary/10 hover:bg-primary/20"
              >
                <MessageSquare className="w-6 h-6 text-primary" />
              </Button>
            </div>
          ) : (
            /* Expanded Agent Panel */
            <div className="h-full flex flex-col">
              {/* Agent Header */}
              <div className="border-b bg-background/80 backdrop-blur-sm p-3">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                    <MessageSquare className="w-4 h-4 text-primary" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-sm">Policy Assistant</h3>
                    <p className="text-xs text-muted-foreground">AI-powered policy guidance</p>
                  </div>
                </div>
              </div>

              {/* Chat Messages */}
              <div className="flex-1 overflow-y-auto premium-scrollbar p-3 space-y-4">
                {messages.length === 0 ? (
                  <div className="bg-background rounded-lg p-3 text-sm border">
                    <div className="text-[11px] uppercase tracking-wide text-muted-foreground mb-1">Welcome</div>
                    <div>Ask a question about your policy. I will show what I understood and apply only the necessary changes to the A4 document.</div>
                  </div>
                ) : (
                  messages.map(msg => (
                    <div key={msg.id} className="space-y-2">
                      {msg.role === 'user' && msg.question && (
                        <div className="bg-background rounded-lg p-3 text-sm border">
                          <div className="text-[11px] uppercase tracking-wide text-muted-foreground mb-1">Question</div>
                          <div className="whitespace-pre-wrap">{msg.question}</div>
                        </div>
                      )}

                      {msg.role === 'assistant' && (
                        <div className="bg-background rounded-lg p-3 text-sm border space-y-3">

                          {/* Understanding Status */}
                          <div>
                            <div className="text-[11px] uppercase tracking-wide text-muted-foreground mb-1">Understood</div>
                            <div className="whitespace-pre-wrap text-foreground/90">{msg.understood}</div>
                          </div>

                          {/* Pending Review State */}
                          {msg.status === 'pending' && msg.actions && msg.actions.length > 0 && (
                            <div className="bg-muted/30 rounded-md p-3 border border-dashed border-primary/20">
                              <div className="flex items-center gap-2 mb-2">
                                <span className="relative flex h-2 w-2">
                                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
                                  <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
                                </span>
                                <span className="text-xs font-semibold text-primary">Proposed Changes</span>
                              </div>

                              <ul className="list-disc pl-4 text-xs space-y-1 mb-3 text-muted-foreground">
                                {msg.actions.map((action, idx) => (
                                  <li key={idx}>
                                    {action.op === 'add' && <span className="text-green-600 font-medium">Add </span>}
                                    {action.op === 'update' && <span className="text-orange-600 font-medium">Update </span>}
                                    {action.op === 'delete' && <span className="text-red-600 font-medium">Delete </span>}
                                    {action.target}
                                    {action.title ? ` "${action.title}"` : ''}
                                  </li>
                                ))}
                              </ul>

                              <div className="flex items-center gap-2">
                                <Button
                                  size="sm"
                                  className="h-7 text-xs bg-green-600 hover:bg-green-700 text-white"
                                  onClick={() => handleApplyActions(msg.id, msg.actions!)}
                                >
                                  <Check className="w-3 h-3 mr-1" />
                                  Apply Changes
                                </Button>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  className="h-7 text-xs hover:bg-destructive/10 hover:text-destructive"
                                  onClick={() => handleDiscardActions(msg.id)}
                                >
                                  Discard
                                </Button>
                              </div>
                            </div>
                          )}

                          {/* Applied State */}
                          {msg.status === 'accepted' && msg.applied && msg.applied.length > 0 && (
                            <div className="mt-2">
                              <div className="text-[11px] uppercase tracking-wide text-green-600 mb-1 flex items-center gap-1">
                                <Check className="w-3 h-3" />
                                Applied changes
                              </div>
                              <ul className="list-disc pl-5 text-xs space-y-1 text-muted-foreground">
                                {msg.applied.map((a, i) => (
                                  <li key={i}>{a}</li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {/* Rejected State */}
                          {msg.status === 'rejected' && (
                            <div className="mt-2 text-xs text-muted-foreground italic">
                              <span className="text-destructive inline-block mr-1">✕</span>
                              Changes discarded by user.
                            </div>
                          )}

                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>

              {/* Chat Input */}
              <div className="border-t bg-background/80 backdrop-blur-sm p-3">
                <div className="rounded-xl border bg-background">
                  {/* Top control row */}
                  <div className="flex items-center justify-between px-2 py-1.5">
                    <div className="flex items-center gap-2">
                      <Button variant="ghost" size="icon" className="h-7 w-7">
                        <AtSign className="w-4 h-4" />
                      </Button>
                      <button className="text-xs px-2 py-1 rounded-full border bg-muted/50 hover:bg-muted transition-colors inline-flex items-center gap-1">
                        <Plus className="w-3 h-3" />
                        Browser
                      </button>
                    </div>
                    <div className="text-[11px] text-muted-foreground inline-flex items-center gap-1">
                      {usagePercent > 0 ? `${usagePercent}%` : ''}
                      <Zap className="w-3 h-3 opacity-70" />
                    </div>
                  </div>
                  {/* Text area */}
                  <div className="px-3 pb-2">
                    <textarea
                      ref={chatInputRef}
                      rows={1}
                      placeholder="Plan, search, build anything"
                      className="w-full resize-none bg-transparent outline-none text-sm min-h-[40px] max-h-40 py-1"
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault()
                          handleSend()
                        }
                      }}
                    />
                  </div>
                  {/* Bottom control row */}
                  <div className="flex items-center justify-between px-2 pb-2">
                    <div className="flex items-center gap-2">
                      {/* Mode pill dropdown */}
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <button
                            className="px-3 h-7 rounded-full border text-xs bg-background hover:bg-accent/50 transition-colors whitespace-nowrap inline-flex items-center gap-2"
                            aria-label="Select chat mode"
                          >
                            <span className="text-primary">∞</span>
                            {chatMode === 'agent' && 'Agent'}
                            {chatMode === 'brainstorm' && 'Brainstorm'}
                            {chatMode === 'memory' && 'Chat w/ memory + policy'}
                            <span className="text-[10px] text-muted-foreground ml-1">Ctrl+I</span>
                          </button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="start" className="w-64">
                          <DropdownMenuRadioGroup value={chatMode} onValueChange={(v) => setChatMode(v as any)}>
                            <DropdownMenuRadioItem value="agent">Agent</DropdownMenuRadioItem>
                            <DropdownMenuRadioItem value="brainstorm">Brainstorm</DropdownMenuRadioItem>
                            <DropdownMenuRadioItem value="memory">Chat with memory and active policy context</DropdownMenuRadioItem>
                          </DropdownMenuRadioGroup>
                        </DropdownMenuContent>
                      </DropdownMenu>
                      {/* Model selector styled like "Auto" */}
                      <Select value={selectedModelId} onValueChange={(v) => setSelectedModelId(v)}>
                        <SelectTrigger className="h-7 w-[9rem] rounded-full px-3 text-xs">
                          <SelectValue placeholder="Auto" />
                        </SelectTrigger>
                        <SelectContent>
                          {availableModels.length === 0 ? (
                            <SelectItem value="no-models" disabled>
                              No models available
                            </SelectItem>
                          ) : (
                            availableModels.map(m => (
                              <SelectItem key={m.id} value={m.id}>
                                {m.name}
                              </SelectItem>
                            ))
                          )}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="flex items-center gap-1">
                      <Button variant="ghost" size="icon" className="h-7 w-7">
                        <ImageIcon className="w-4 h-4" />
                      </Button>
                      <Button size="icon" className="h-8 w-8 rounded-full" onClick={handleSend} disabled={isAIGenerating}>
                        <CornerUpRight className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                </div>
                <div className="mt-2 text-xs text-muted-foreground">
                  {isAIGenerating ? 'Generating with ' + (availableModels.find(m => m.id === selectedModelId)?.name || 'model') + '...' : 'Shift+Enter for newline · Enter to send'}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* A4 Policy Canvas Panel */}
        <div ref={a4PanelRef} className={`${layoutClasses.right} transition-all duration-300 ease-in-out ${isSwapped ? 'border-r' : 'border-l'} bg-background/50 relative`}>
          {/* Document Controls */}
          <div className="border-b bg-background/80 backdrop-blur-sm p-3">
            <div className="flex items-center justify-between">
              {/* Left Side - Return Button and Policy Crafter Title */}
              <div className="flex items-center gap-3">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={onReturnToChat}
                  className="gap-2 hover:bg-primary/10 h-7 px-2 text-xs font-medium"
                >
                  <ArrowLeft className="w-3 h-3" />
                  <span>Return to Chat</span>
                </Button>

                <div className="w-px h-4 bg-border" />

                <div className="flex items-center gap-2">
                  <div className="bg-primary text-primary-foreground text-xs font-semibold px-2 py-1 rounded-full">
                    Alpha
                  </div>
                  <h1 className="text-base font-semibold">Policy Crafter</h1>
                </div>
              </div>

              {/* Center Controls - Templates and Document Actions */}
              <div className="flex items-center gap-4">
                {/* Template Selection Button */}
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowTemplatePopup(!showTemplatePopup)}
                  className="h-7 px-3 text-xs gap-1"
                  title="Select Template"
                >
                  <File className="w-3 h-3" />
                  <span>Templates</span>
                  {getCurrentTemplateFromPages() !== 'none' && getCurrentTemplateFromPages() !== 'mixed' && (
                    <div className="w-2 h-2 bg-primary rounded-full"></div>
                  )}
                  {getCurrentTemplateFromPages() === 'mixed' && (
                    <div className="w-2 h-2 bg-orange-500 rounded-full"></div>
                  )}
                </Button>

                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleFitToWidth}
                  className="h-7 px-2 text-xs"
                  title="Fit to Width"
                >
                  <Maximize className="w-3 h-3 mr-1" />
                  Fit
                </Button>

                {/* Page Counter */}
                <div className="flex items-center gap-1 bg-muted/50 rounded-lg p-1">
                  <div className="px-2 py-1 text-xs font-medium min-w-[4rem] text-center">
                    {pages.length} pages
                  </div>
                </div>

                {/* Add Page Button */}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={addPage}
                  className="h-7 px-2 text-xs gap-1"
                  title="Add Page"
                >
                  <Plus className="w-3 h-3" />
                  <span>Add</span>
                </Button>

                {/* Document Actions */}
                <div className="flex items-center gap-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleRotate}
                    className="h-7 w-7 p-0"
                    title="Rotate Document"
                  >
                    <RotateCcw className="w-3 h-3" />
                  </Button>

                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleDownload}
                    className="h-7 w-7 p-0"
                    title="Download PDF"
                  >
                    <Download className="w-3 h-3" />
                  </Button>

                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handlePrint}
                    className="h-7 w-7 p-0"
                    title="Print Document"
                  >
                    <Printer className="w-3 h-3" />
                  </Button>
                </div>
              </div>

              {/* Layout Controls - Right Side */}
              <div className="flex items-center gap-1">
                <div className="flex items-center gap-1 bg-muted/50 rounded-lg p-1">
                  <Button
                    variant={layoutState === 'focus' ? 'default' : 'ghost'}
                    size="sm"
                    onClick={() => setLayoutState('focus')}
                    className="h-7 w-7 p-0"
                    title="Focus Mode"
                  >
                    <Minimize2 className="w-3 h-3" />
                  </Button>
                  <Button
                    variant={layoutState === 'default' ? 'default' : 'ghost'}
                    size="sm"
                    onClick={() => setLayoutState('default')}
                    className="h-7 w-7 p-0"
                    title="Default Layout"
                  >
                    <ChevronLeft className="w-3 h-3" />
                  </Button>
                  <Button
                    variant={layoutState === 'deep-assist' ? 'default' : 'ghost'}
                    size="sm"
                    onClick={() => setLayoutState('deep-assist')}
                    className="h-7 w-7 p-0"
                    title="Deep Assist Mode"
                  >
                    <ChevronRight className="w-3 h-3" />
                  </Button>
                  <Button
                    variant={layoutState === 'full-agent' ? 'default' : 'ghost'}
                    size="sm"
                    onClick={() => setLayoutState('full-agent')}
                    className="h-7 w-7 p-0"
                    title="Full Agent Mode"
                  >
                    <Maximize2 className="w-3 h-3" />
                  </Button>
                </div>

                <Button
                  variant={isSwapped ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => setIsSwapped(!isSwapped)}
                  className="h-7 w-7 p-0"
                  title="Switch sides"
                >
                  <ArrowLeftRight className="w-3 h-3" />
                </Button>
              </div>
            </div>
          </div>

          <div className="h-full overflow-y-auto premium-scrollbar p-6 relative">
            <div className="flex flex-col items-center space-y-8">
              {/* Render all pages */}
              {pages.map((page, index) => (
                <div key={page.id} className="relative">
                  {/* Page number indicator - Enhanced visual */}
                  <div className="absolute top-4 -left-10 bg-gradient-to-r from-primary/10 to-primary/5 text-primary text-xs font-semibold px-2 py-1 rounded-lg border border-primary/20 shadow-sm backdrop-blur-sm z-10">
                    <div className="flex items-center gap-1">
                      <div className="w-1.5 h-1.5 bg-primary rounded-full"></div>
                      <span>{index + 1}</span>
                    </div>
                  </div>
                  {renderPage(page, index)}
                </div>
              ))}
            </div>

            {/* Zoom Controls Overlay - Fixed A4 Bottom Right */}
            <div className="fixed bottom-6 z-10" style={{
              right: `calc(${getZoomPosition()})`
            }}>
              <div className={`${micaBackground} backdrop-blur-md border border-border/50 rounded-lg shadow-lg p-3 relative overflow-hidden`}>
                {/* Mica effect overlay */}
                <div className="absolute inset-0 bg-gradient-to-br from-white/20 via-transparent to-transparent rounded-lg"></div>
                <div className="relative z-10">
                  <div className="flex flex-col items-center gap-3">
                    {/* Zoom Label */}
                    <div className={`text-xs font-medium ${zoomTextColor} tracking-wide`}>Zoom</div>

                    {/* Vertical Controls */}
                    <div className="flex flex-col items-center gap-1.5 bg-background/50 backdrop-blur-sm border border-border/30 rounded-md p-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={handleZoomIn}
                        disabled={zoomLevel >= 300}
                        className="h-7 w-7 p-0 rounded-md hover:bg-accent/50"
                        title="Zoom In"
                      >
                        <ZoomIn className="w-3.5 h-3.5" />
                      </Button>

                      <div className={`px-2 py-1 text-xs font-semibold min-w-[3rem] text-center ${zoomTextColor} rounded-sm bg-muted/30 border border-border/20`}>
                        {zoomLevel}%
                      </div>

                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={handleZoomOut}
                        disabled={zoomLevel <= 50}
                        className="h-7 w-7 p-0 rounded-md hover:bg-accent/50"
                        title="Zoom Out"
                      >
                        <ZoomOut className="w-3.5 h-3.5" />
                      </Button>
                    </div>

                    {/* Reset Button */}
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleZoomReset}
                      className="h-7 px-3 text-xs rounded-md border-border/40 bg-background/30 hover:bg-accent/20"
                      title="Reset Zoom"
                    >
                      Reset
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Template Selection Center Popup */}
      {showTemplatePopup && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center">
          <div className="bg-background border rounded-lg shadow-xl p-6 max-w-md w-full mx-4" data-template-popup>
            <div className="text-center mb-6">
              <h2 className="text-lg font-semibold mb-2">Load Template</h2>
              <p className="text-sm text-muted-foreground">Choose how to apply the template</p>
              {getCurrentTemplateFromPages() !== 'none' && (
                <div className="mt-2 px-3 py-1 bg-muted rounded-full text-xs">
                  Current: {getCurrentTemplateFromPages() === 'mixed' ? 'Mixed templates' :
                    getCurrentTemplateFromPages() === 'indian-education' ? 'NEP 2020' :
                      getCurrentTemplateFromPages() === 'gitam-education' ? 'GITAM Policy' : 'Blank'}
                </div>
              )}
            </div>

            <div className="space-y-4">
              {/* Template Options */}
              <div className="space-y-3">
                <Button
                  variant="outline"
                  size="lg"
                  onClick={() => handleTemplateLoad('indian-education')}
                  className="w-full justify-start h-12 px-4 gap-3"
                >
                  <Book className="w-5 h-5" />
                  <div className="text-left">
                    <div className="font-medium">NEP 2020</div>
                    <div className="text-xs text-muted-foreground">Apply to all pages</div>
                  </div>
                </Button>

                <Button
                  variant="outline"
                  size="lg"
                  onClick={() => handleTemplateLoad('gitam-education')}
                  className="w-full justify-start h-12 px-4 gap-3"
                >
                  <GraduationCap className="w-5 h-5" />
                  <div className="text-left">
                    <div className="font-medium">GITAM Policy</div>
                    <div className="text-xs text-muted-foreground">Apply to all pages</div>
                  </div>
                </Button>

                <Button
                  variant="outline"
                  size="lg"
                  onClick={() => handleTemplateLoad('none')}
                  className="w-full justify-start h-12 px-4 gap-3"
                >
                  <File className="w-5 h-5" />
                  <div className="text-left">
                    <div className="font-medium">Blank Document</div>
                    <div className="text-xs text-muted-foreground">Apply to all pages</div>
                  </div>
                </Button>
              </div>

              {/* Divider */}
              <div className="border-t pt-4">
                <p className="text-xs text-muted-foreground text-center mb-3">Or add as new page</p>

                <div className="grid grid-cols-3 gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleTemplateLoadToNewPage('indian-education')}
                    className="h-10 flex flex-col gap-1"
                  >
                    <Book className="w-4 h-4" />
                    <span className="text-xs">NEP</span>
                  </Button>

                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleTemplateLoadToNewPage('gitam-education')}
                    className="h-10 flex flex-col gap-1"
                  >
                    <GraduationCap className="w-4 h-4" />
                    <span className="text-xs">GITAM</span>
                  </Button>

                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleTemplateLoadToNewPage('none')}
                    className="h-10 flex flex-col gap-1"
                  >
                    <File className="w-4 h-4" />
                    <span className="text-xs">Blank</span>
                  </Button>
                </div>
              </div>
            </div>

            <div className="mt-6 pt-4 border-t">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowTemplatePopup(false)}
                className="w-full"
              >
                Cancel
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
