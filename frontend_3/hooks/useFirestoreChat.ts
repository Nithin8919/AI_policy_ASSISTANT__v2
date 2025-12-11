'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import {
  collection,
  doc,
  addDoc,
  updateDoc,
  deleteDoc,
  query,
  orderBy,
  onSnapshot,
  serverTimestamp,
  Timestamp,
  getDoc,
  setDoc,
  writeBatch,
  where
} from 'firebase/firestore'
import { db } from '@/lib/firebase'
import { queryAPI, queryWithFiles, type QueryResponse } from '@/lib/api'

// Types
export interface Message {
  id: string
  content: string
  role: 'user' | 'assistant' | 'system'
  timestamp: Date
  response?: QueryResponse & { error?: { code: string; message: string; details?: any } }
  queryMode?: 'qa' | 'deep_think' | 'brainstorm'
  isThinking?: boolean
  currentStep?: string
  attachedFiles?: { name: string; size: number; type: string }[]
}

export interface Draft {
  id: string
  title: string
  content: string
  createdAt: Date
  updatedAt: Date
}

export interface Chat {
  id: string
  title: string
  createdAt: Date
  updatedAt: Date
  activeDraftId?: string | null
}

// Firestore schema:
// /chats/{chatId}
//   - title: string
//   - createdAt: Timestamp
//   - updatedAt: Timestamp
//   - activeDraftId?: string
// /chats/{chatId}/messages/{messageId}
//   - content: string
//   - role: 'user' | 'assistant' | 'system'
//   - timestamp: Timestamp
//   - response?: object (QueryResponse with optional error field)
//   - queryMode?: string
//   - attachedFiles?: array
// /chats/{chatId}/drafts/{draftId}
//   - title: string
//   - content: string
//   - createdAt: Timestamp
//   - updatedAt: Timestamp

export function useFirestoreChat() {
  const [currentChatId, setCurrentChatId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [drafts, setDrafts] = useState<Draft[]>([])
  const [activeDraftId, setActiveDraftId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  
  // Refs to track listeners
  const messagesUnsubscribeRef = useRef<(() => void) | null>(null)
  const draftsUnsubscribeRef = useRef<(() => void) | null>(null)
  const chatUnsubscribeRef = useRef<(() => void) | null>(null)

  // Helper to convert Firestore timestamp to Date
  const toDate = (timestamp: Timestamp | Date | null | undefined): Date => {
    if (!timestamp) return new Date()
    if (timestamp instanceof Date) return timestamp
    if (timestamp.toDate) return timestamp.toDate()
    return new Date()
  }

  // Helper to sanitize message data (remove undefined fields)
  const sanitizeMessage = (msg: Partial<Message>): any => {
    const clean: any = {}
    Object.keys(msg).forEach(key => {
      const value = msg[key as keyof Message]
      if (value !== undefined && value !== null) {
        clean[key] = value
      }
    })
    return clean
  }

  // Clean up listeners when chat changes
  useEffect(() => {
    return () => {
      messagesUnsubscribeRef.current?.()
      draftsUnsubscribeRef.current?.()
      chatUnsubscribeRef.current?.()
    }
  }, [])

  // Subscribe to messages for current chat
  useEffect(() => {
    if (!currentChatId) {
      setMessages([])
      setDrafts([])
      setActiveDraftId(null)
      setLoading(false)
      return
    }

    setLoading(true)

    // Subscribe to messages
    const messagesRef = collection(db, 'chats', currentChatId, 'messages')
    const messagesQuery = query(messagesRef, orderBy('timestamp', 'asc'))
    
    messagesUnsubscribeRef.current = onSnapshot(
      messagesQuery,
      (snapshot) => {
        const msgs: Message[] = snapshot.docs.map(doc => {
          const data = doc.data()
          return {
            id: doc.id,
            content: data.content || '',
            role: data.role || 'user',
            timestamp: toDate(data.timestamp),
            response: data.response,
            queryMode: data.queryMode,
            isThinking: data.isThinking,
            currentStep: data.currentStep,
            attachedFiles: data.attachedFiles
          }
        })
        setMessages(msgs)
        setLoading(false)
      },
      (error) => {
        console.error('Error listening to messages:', error)
        setLoading(false)
      }
    )

    // Subscribe to drafts
    const draftsRef = collection(db, 'chats', currentChatId, 'drafts')
    const draftsQuery = query(draftsRef, orderBy('createdAt', 'asc'))
    
    draftsUnsubscribeRef.current = onSnapshot(
      draftsQuery,
      (snapshot) => {
        const draftList: Draft[] = snapshot.docs.map(doc => {
          const data = doc.data()
          return {
            id: doc.id,
            title: data.title || 'Draft',
            content: data.content || '',
            createdAt: toDate(data.createdAt),
            updatedAt: toDate(data.updatedAt)
          }
        })
        setDrafts(draftList)
        
        // If no active draft and we have drafts, set first one as active
        if (!activeDraftId && draftList.length > 0) {
          setActiveDraftId(draftList[0].id)
        }
      },
      (error) => {
        console.error('Error listening to drafts:', error)
      }
    )

    // Subscribe to chat metadata (for activeDraftId)
    const chatRef = doc(db, 'chats', currentChatId)
    chatUnsubscribeRef.current = onSnapshot(
      chatRef,
      (snapshot) => {
        if (snapshot.exists()) {
          const data = snapshot.data()
          if (data.activeDraftId) {
            setActiveDraftId(data.activeDraftId)
          }
        }
      },
      (error) => {
        console.error('Error listening to chat:', error)
      }
    )

    return () => {
      messagesUnsubscribeRef.current?.()
      draftsUnsubscribeRef.current?.()
      chatUnsubscribeRef.current?.()
    }
  }, [currentChatId, activeDraftId])

  // Create a new chat
  const createChat = useCallback(async (): Promise<string> => {
    try {
      // Create chat document
      const chatRef = doc(collection(db, 'chats'))
      const now = serverTimestamp()
      
      // Create default draft
      const defaultDraft: Draft = {
        id: '', // Will be set after creation
        title: 'Draft 1',
        content: '',
        createdAt: new Date(),
        updatedAt: new Date()
      }
      
      const draftRef = doc(collection(db, 'chats', chatRef.id, 'drafts'))
      const draftId = draftRef.id
      
      // Use batch to ensure atomicity
      const batch = writeBatch(db)
      
      batch.set(chatRef, {
        title: 'New Chat',
        createdAt: now,
        updatedAt: now,
        activeDraftId: draftId
      })
      
      batch.set(draftRef, {
        title: defaultDraft.title,
        content: defaultDraft.content,
        createdAt: now,
        updatedAt: now
      })
      
      await batch.commit()
      
      setCurrentChatId(chatRef.id)
      return chatRef.id
    } catch (error) {
      console.error('Error creating chat:', error)
      throw error
    }
  }, [])

  // Send a message (user message + get assistant response)
  const sendMessage = useCallback(async (
    content: string,
    files?: File[],
    queryMode: 'qa' | 'deep_think' | 'brainstorm' = 'qa',
    internetEnabled: boolean = false
  ): Promise<void> => {
    if (!currentChatId) {
      // Create chat if none exists
      const newChatId = await createChat()
      setCurrentChatId(newChatId)
      // Recursively call with new chat ID
      return sendMessage(content, files, queryMode, internetEnabled)
    }

    setSending(true)

    try {
      // 1. Save user message to Firestore
      const userMessage: Partial<Message> = {
        content,
        role: 'user',
        timestamp: new Date(),
        queryMode,
        attachedFiles: files?.map(f => ({
          name: f.name,
          size: f.size,
          type: f.type
        }))
      }

      const messagesRef = collection(db, 'chats', currentChatId, 'messages')
      await addDoc(messagesRef, {
        ...sanitizeMessage(userMessage),
        timestamp: serverTimestamp()
      })

      // Update chat title from first user message
      const chatRef = doc(db, 'chats', currentChatId)
      const chatSnap = await getDoc(chatRef)
      if (chatSnap.exists()) {
        const chatData = chatSnap.data()
        if (chatData.title === 'New Chat') {
          const newTitle = content.length > 30 ? content.substring(0, 30) + '...' : content
          await updateDoc(chatRef, {
            title: newTitle,
            updatedAt: serverTimestamp()
          })
        }
      }

      // 2. Call backend API
      let response: QueryResponse
      const conversationHistory = messages
        .filter(msg => msg.role === 'user' || msg.role === 'assistant')
        .slice(-10)
        .map(msg => ({
          role: msg.role,
          content: msg.content
        }))

      try {
        if (files && files.length > 0) {
          response = await queryWithFiles(
            content,
            files,
            queryMode,
            internetEnabled,
            conversationHistory
          )
        } else {
          response = await queryAPI({
            query: content,
            simulate_failure: false,
            mode: queryMode,
            internet_enabled: internetEnabled,
            conversation_history: conversationHistory
          })
        }
      } catch (apiError) {
        // Handle API errors properly
        const errorResponse: QueryResponse & { error?: { code: string; message: string; details?: any } } = {
          answer: '',
          citations: [],
          processing_trace: {
            language: 'en',
            retrieval: { dense: [], sparse: [] },
            kg_traversal: '',
            controller_iterations: 0
          },
          risk_assessment: 'high',
          error: {
            code: 'API_ERROR',
            message: apiError instanceof Error ? apiError.message : 'Unknown API error',
            details: apiError
          }
        }
        response = errorResponse
      }

      // 3. Save assistant message to Firestore
      const assistantMessage: Partial<Message> = {
        content: response.answer || (response as any).error?.message || 'No response generated',
        role: 'assistant',
        timestamp: new Date(),
        response: response,
        queryMode
      }

      await addDoc(messagesRef, {
        ...sanitizeMessage(assistantMessage),
        timestamp: serverTimestamp()
      })

      // Update chat updatedAt
      await updateDoc(chatRef, {
        updatedAt: serverTimestamp()
      })

    } catch (error) {
      console.error('Error sending message:', error)
      
      // Save error message to Firestore
      const messagesRef = collection(db, 'chats', currentChatId, 'messages')
      const errorMessage: Partial<Message> = {
        content: `I apologize, but I encountered an error: ${error instanceof Error ? error.message : 'Unknown error occurred'}`,
        role: 'system',
        timestamp: new Date(),
        response: {
          answer: '',
          citations: [],
          processing_trace: {
            language: 'en',
            retrieval: { dense: [], sparse: [] },
            kg_traversal: '',
            controller_iterations: 0
          },
          risk_assessment: 'high',
          error: {
            code: 'SYSTEM_ERROR',
            message: error instanceof Error ? error.message : 'Unknown error',
            details: error
          }
        }
      }
      
      await addDoc(messagesRef, {
        ...sanitizeMessage(errorMessage),
        timestamp: serverTimestamp()
      })
    } finally {
      setSending(false)
    }
  }, [currentChatId, messages, createChat])

  // Draft management
  const createDraft = useCallback(async (): Promise<string> => {
    if (!currentChatId) {
      const newChatId = await createChat()
      setCurrentChatId(newChatId)
      return createDraft()
    }

    const draftCount = drafts.length + 1
    const draftRef = doc(collection(db, 'chats', currentChatId, 'drafts'))
    const draftId = draftRef.id

    await setDoc(draftRef, {
      title: `Draft ${draftCount}`,
      content: '',
      createdAt: serverTimestamp(),
      updatedAt: serverTimestamp()
    })

    // Set as active draft
    const chatRef = doc(db, 'chats', currentChatId)
    await updateDoc(chatRef, {
      activeDraftId: draftId,
      updatedAt: serverTimestamp()
    })

    return draftId
  }, [currentChatId, drafts.length, createChat])

  const updateDraftContent = useCallback(async (draftId: string, content: string): Promise<void> => {
    if (!currentChatId) return

    const draftRef = doc(db, 'chats', currentChatId, 'drafts', draftId)
    await updateDoc(draftRef, {
      content,
      updatedAt: serverTimestamp()
    })
  }, [currentChatId])

  const appendToDraft = useCallback(async (content: string): Promise<void> => {
    if (!currentChatId || !activeDraftId) return

    const draftRef = doc(db, 'chats', currentChatId, 'drafts', activeDraftId)
    const draftSnap = await getDoc(draftRef)
    
    if (draftSnap.exists()) {
      const currentContent = draftSnap.data().content || ''
      const separator = currentContent ? '\n\n---\n\n' : ''
      const newContent = `${currentContent}${separator}${content}`
      
      await updateDoc(draftRef, {
        content: newContent,
        updatedAt: serverTimestamp()
      })
    }
  }, [currentChatId, activeDraftId])

  const setActiveDraft = useCallback(async (draftId: string): Promise<void> => {
    if (!currentChatId) return

    const chatRef = doc(db, 'chats', currentChatId)
    await updateDoc(chatRef, {
      activeDraftId: draftId,
      updatedAt: serverTimestamp()
    })
  }, [currentChatId])

  const renameDraft = useCallback(async (draftId: string, newTitle: string): Promise<void> => {
    if (!currentChatId) return

    const draftRef = doc(db, 'chats', currentChatId, 'drafts', draftId)
    await updateDoc(draftRef, {
      title: newTitle,
      updatedAt: serverTimestamp()
    })
  }, [currentChatId])

  const deleteDraft = useCallback(async (draftId: string): Promise<void> => {
    if (!currentChatId || drafts.length <= 1) {
      alert('Cannot delete the last draft. At least one draft must exist.')
      return
    }

    const draftRef = doc(db, 'chats', currentChatId, 'drafts', draftId)
    await deleteDoc(draftRef)

    // If deleting active draft, switch to first remaining draft
    if (activeDraftId === draftId && drafts.length > 1) {
      const remainingDrafts = drafts.filter(d => d.id !== draftId)
      if (remainingDrafts.length > 0) {
        await setActiveDraft(remainingDrafts[0].id)
      }
    }
  }, [currentChatId, drafts, activeDraftId, setActiveDraft])

  // Get active draft
  const activeDraft = drafts.find(d => d.id === activeDraftId) || drafts[0] || null

  return {
    // State
    currentChatId,
    messages,
    drafts,
    activeDraft,
    activeDraftId,
    loading,
    sending,
    
    // Actions
    setCurrentChatId,
    createChat,
    sendMessage,
    createDraft,
    updateDraftContent,
    appendToDraft,
    setActiveDraft,
    renameDraft,
    deleteDraft
  }
}


