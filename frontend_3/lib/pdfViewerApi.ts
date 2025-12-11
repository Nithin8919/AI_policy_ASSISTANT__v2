/**
 * PDF Viewer API Service
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface PdfUrlResponse {
  signedUrl: string
  expiresAt: string
  doc_id: string
  pdf_filename: string
}

export interface LocateSnippetRequest {
  doc_id: string
  snippet: string
}

export interface LocateSnippetResponse {
  page: number | null
  found: boolean
  normalizedSnippet: string
  matchConfidence: 'exact' | 'none'
  totalPages: number
  error?: string
}

export async function getPdfUrl(
  docId: string,
  expirationMinutes: number = 60,
  sourceHint?: string
): Promise<PdfUrlResponse> {
  const url = new URL(`${API_BASE_URL}/api/pdf-url`)
  url.searchParams.set('doc_id', docId)
  url.searchParams.set('expiration_minutes', expirationMinutes.toString())
  if (sourceHint) {
    url.searchParams.set('source_hint', sourceHint)
  }

  const response = await fetch(url.toString(), {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(error.detail || `Failed to get PDF URL: ${response.statusText}`)
  }

  return response.json()
}

export async function locateSnippet(
  docId: string,
  snippet: string
): Promise<LocateSnippetResponse> {
  const response = await fetch(`${API_BASE_URL}/api/locate-snippet`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      doc_id: docId,
      snippet: snippet,
    }),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(error.detail || `Failed to locate snippet: ${response.statusText}`)
  }

  return response.json()
}

export async function openPdfAtSnippet(
  docId: string,
  snippet: string
): Promise<{
  pdfUrl: string
  page: number | null
  found: boolean
  expiresAt: string
}> {
  const [pdfUrlData, snippetData] = await Promise.all([
    getPdfUrl(docId),
    locateSnippet(docId, snippet),
  ])

  return {
    pdfUrl: pdfUrlData.signedUrl,
    page: snippetData.page,
    found: snippetData.found,
    expiresAt: pdfUrlData.expiresAt,
  }
}
