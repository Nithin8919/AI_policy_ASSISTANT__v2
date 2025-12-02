export interface QueryRequest {
  query: string
  simulate_failure?: boolean
  mode?: string
  internet_enabled?: boolean

}

export interface Citation {
  docId: string
  page: number
  span: string
}

export interface RetrievalResult {
  dense: string[]
  sparse: string[]
}

export interface ProcessingTrace {
  language: string
  retrieval: RetrievalResult
  kg_traversal: string
  controller_iterations: number
}

export interface QueryResponse {
  answer: string
  citations: Citation[]
  processing_trace: ProcessingTrace
  risk_assessment: string
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function queryAPI(request: QueryRequest): Promise<QueryResponse> {
  try {
    console.log('🔵 QueryAPI called with:', request)
    console.log('🔵 API_BASE_URL:', API_BASE_URL)
    console.log('🔵 Full URL:', `${API_BASE_URL}/v1/query`)
    
    const response = await fetch(`${API_BASE_URL}/v1/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    })

    console.log('🟢 Response status:', response.status)
    console.log('🟢 Response ok:', response.ok)
    console.log('🟢 Response headers:', Object.fromEntries(response.headers.entries()))

    if (!response.ok) {
      const errorText = await response.text()
      console.error('❌ Response error text:', errorText)
      throw new Error(`API request failed: ${response.status} ${response.statusText} - ${errorText}`)
    }

    const data = await response.json()
    console.log('✅ Response data:', data)
    return data
  } catch (error) {
    console.error('❌ Error calling query API:', error)
    console.error('❌ Error type:', typeof error)
    console.error('❌ Error message:', error instanceof Error ? error.message : String(error))
    throw error
  }
}


export async function getSystemStatus(): Promise<any> {
  try {
    const response = await fetch(`${API_BASE_URL}/v1/status`)
    
    if (!response.ok) {
      throw new Error(`Status check failed: ${response.status} ${response.statusText}`)
    }

    return await response.json()
  } catch (error) {
    console.error('Error checking system status:', error)
    throw error
  }
}

export async function scrapeUrl(url: string, method: string = 'auto'): Promise<any> {
  try {
    const response = await fetch(`${API_BASE_URL}/v1/scrape`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        url,
        method,
        max_retries: 3,
      }),
    })

    if (!response.ok) {
      throw new Error(`Scraping failed: ${response.status} ${response.statusText}`)
    }

    return await response.json()
  } catch (error) {
    console.error('Error scraping URL:', error)
    throw error
  }
}

export async function getDocument(documentId: string): Promise<any> {
  try {
    const response = await fetch(`${API_BASE_URL}/v1/document/${documentId}`)
    
    if (!response.ok) {
      throw new Error(`Document retrieval failed: ${response.status} ${response.statusText}`)
    }

    return await response.json()
  } catch (error) {
    console.error('Error retrieving document:', error)
    throw error
  }
}

export async function submitFeedback(
  query: string,
  response: string,
  rating: number,
  comments?: string
): Promise<any> {
  try {
    const apiResponse = await fetch(`${API_BASE_URL}/v1/feedback`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query,
        response,
        rating,
        comments,
      }),
    })

    if (!apiResponse.ok) {
      throw new Error(`Feedback submission failed: ${apiResponse.status} ${apiResponse.statusText}`)
    }

    return await apiResponse.json()
  } catch (error) {
    console.error('Error submitting feedback:', error)
    throw error
  }
}

export async function queryModelDirect(request: QueryRequest): Promise<QueryResponse> {
  return queryAPI(request)
}


export async function queryWithFiles(
  query: string,
  files: File[],
  mode: string = 'qa',
  internet_enabled: boolean = false
): Promise<QueryResponse> {
  try {
    console.log('🔵 QueryWithFiles called with:', { query, fileCount: files.length, mode, internet_enabled })
    
    const formData = new FormData()
    formData.append('query', query)
    formData.append('mode', mode)
    formData.append('internet_enabled', internet_enabled.toString())
    
    files.forEach((file) => {
      formData.append('files', file)
    })
    
    const response = await fetch(`${API_BASE_URL}/v3/query_with_files`, {
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      const errorText = await response.text()
      throw new Error(`API request failed: ${response.status} - ${errorText}`)
    }

    const data = await response.json()
    console.log('✅ File upload response:', data)
    return data
  } catch (error) {
    console.error('❌ Error calling query with files API:', error)
    throw error
  }
}
