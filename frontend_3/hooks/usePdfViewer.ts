'use client'

import { useState, useCallback } from 'react'
import { openPdfAtSnippet, getPdfUrl } from '@/lib/pdfViewerApi'

export interface PdfViewerState {
  isOpen: boolean
  pdfUrl: string | null
  pageNumber: number | null
  highlightText: string | null
  title: string | null
  loading: boolean
  error: string | null
}

export function usePdfViewer() {
  const [state, setState] = useState<PdfViewerState>({
    isOpen: false,
    pdfUrl: null,
    pageNumber: null,
    highlightText: null,
    title: null,
    loading: false,
    error: null,
  })

  const openWithSnippet = useCallback(async (
    docId: string,
    snippet: string,
    title?: string
  ) => {
    setState((prev) => ({
      ...prev,
      loading: true,
      error: null,
      isOpen: true,
    }))

    try {
      const result = await openPdfAtSnippet(docId, snippet)

      setState({
        isOpen: true,
        pdfUrl: result.pdfUrl,
        pageNumber: result.page || 1,
        highlightText: snippet,
        title: title || docId,
        loading: false,
        error: result.found
          ? null
          : 'Snippet not found in PDF. Showing first page.',
      })
    } catch (error) {
      console.error('Error opening PDF:', error)
      setState((prev) => ({
        ...prev,
        loading: false,
        error: error instanceof Error ? error.message : 'Failed to open PDF',
      }))
    }
  }, [])

  const openPdf = useCallback(async (
    docId: string,
    title?: string,
    pageNumber: number = 1,
    sourceHint?: string
  ) => {
    setState((prev) => ({
      ...prev,
      loading: true,
      error: null,
      isOpen: true,
    }))

    try {
      const result = await getPdfUrl(docId, 60, sourceHint)

      setState({
        isOpen: true,
        pdfUrl: result.signedUrl,
        pageNumber: pageNumber,
        highlightText: null,
        title: title || result.pdf_filename,
        loading: false,
        error: null,
      })
    } catch (error) {
      console.error('Error opening PDF:', error)
      setState((prev) => ({
        ...prev,
        loading: false,
        error: error instanceof Error ? error.message : 'Failed to open PDF',
      }))
    }
  }, [])

  const closePdf = useCallback(() => {
    setState({
      isOpen: false,
      pdfUrl: null,
      pageNumber: null,
      highlightText: null,
      title: null,
      loading: false,
      error: null,
    })
  }, [])

  return {
    state,
    openWithSnippet,
    openPdf,
    closePdf,
  }
}
