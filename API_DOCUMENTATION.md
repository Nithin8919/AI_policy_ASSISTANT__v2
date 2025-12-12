# API Documentation

This document provides a comprehensive overview of the API for the AP Policy Assistant project. It covers the frontend API calls, backend endpoints, and the legacy answer generation system.

## 1. Architecture Overview

The system is composed of three main components: a frontend application, a backend retrieval system, and a legacy answer generation module. The following diagram illustrates the high-level architecture:

```
+-----------------+      +----------------------+      +--------------------------+
|                 |      |                      |      |                          |
|    Frontend     |----->|   Backend (v3)       |----->| Legacy Answer Generation |
| (Next.js)       |      | (FastAPI)            |      | (retrieval/answer_generator.py) |
|                 |      |                      |      |                          |
+-----------------+      +----------------------+      +--------------------------+
       |                        |                                |
       |                        |                                |
       v                        v                                v
- Makes API calls to the    - Exposes REST endpoints        - Generates answers from
  backend                   - Handles business logic          retrieved context
- Renders UI components     - Manages data flow             - Builds prompts for LLM
                            - Integrates with legacy
                              answer generation
```

## 2. Frontend API Calls

The frontend application, located in the `frontend` directory, communicates with the backend through a set of API calls defined in `frontend/lib/api.ts`.

### 2.1. `queryAPI`

-   **Purpose**: Submits a query to the backend without any file attachments.
-   **Request Shape**:
    ```typescript
    export interface QueryRequest {
      query: string;
      simulate_failure?: boolean;
      mode?: 'qa' | 'deep_think' | 'brainstorm';
      internet_enabled?: boolean;
      conversation_history?: Array<{ role: string; content: string }>;
    }
    ```
-   **Response Shape**:
    ```typescript
    export interface QueryResponse {
      answer: string;
      citations: Array<{
        docId: string;
        page: number;
        span: string;
        source: string;
        vertical: string;
        url?: string;
      }>;
      processing_trace: {
        language: string;
        retrieval: {
          verticals_searched: string[];
          processing_time: number;
          total_candidates: number;
          final_count: number;
          cache_hits: number;
          rewrites_count: number;
        };
        kg_traversal: string;
        controller_iterations: number;
        steps: string[];
      };
      risk_assessment: string;
      performance_metrics: {
        total_time: number;
        retrieval_time: number;
        answer_time: number;
        cache_hit_rate: number;
        verticals_searched: number;
        rewrites_generated: number;
        candidates_processed: number;
        parallel_processing: boolean;
      };
    }
    ```
-   **Auth Flow**: No authentication is required for this endpoint.
-   **UI Usage**: This function is called from the `ChatBot.tsx` component when a user sends a message without attaching any files.

### 2.2. `queryWithFiles`

-   **Purpose**: Submits a query to the backend along with one or more file attachments.
-   **Request Shape**:
    ```typescript
    export interface QueryWithFilesRequest {
      query: string;
      files: File[];
      mode: 'qa' | 'deep_think' | 'brainstorm';
      internet_enabled: boolean;
      conversation_history?: Array<{ role: string; content: string }>;
    }
    ```
-   **Response Shape**: Same as `QueryResponse`.
-   **Auth Flow**: No authentication is required for this endpoint.
-   **UI Usage**: This function is called from the `ChatBot.tsx` component when a user sends a message with attached files.

## 3. Backend Endpoints

The backend, located in the `retrieval_v3` directory, exposes the following endpoints.

### 3.1. `/v1/query`

-   **Purpose**: Legacy endpoint that redirects to the `/v3/query` endpoint.
-   **Method and URL**: `POST /v1/query`
-   **Request Schema**: See `/v3/query`.
-   **Response Schema**: See `/v3/query`.
-   **Example Request**:
    ```bash
    curl -X POST "http://localhost:8000/v1/query" -H "Content-Type: application/json" -d '{
      "query": "What is Section 12 RTE Act?",
      "mode": "qa"
    }'
    ```
-   **Example Response**: See `/v3/query`.
-   **Dependencies**: This endpoint has no direct dependencies as it only redirects to the `/v3/query` endpoint.

### 3.2. `/v3/query`

-   **Purpose**: Handles queries that do not include file uploads.
-   **Method and URL**: `POST /v3/query`
-   **Request Schema**:
    ```json
    {
      "query": "string",
      "mode": "string (qa, deep_think, or brainstorm)",
      "top_k": "integer (optional)",
      "internet_enabled": "boolean (optional)",
      "conversation_history": "array (optional)"
    }
    ```
-   **Response Schema**:
    ```json
    {
      "answer": "string",
      "citations": "array",
      "processing_trace": "object",
      "risk_assessment": "string",
      "performance_metrics": "object"
    }
    ```
-   **Example Request**:
    ```bash
    curl -X POST "http://localhost:8000/v3/query" -H "Content-Type: application/json" -d '{
      "query": "What are the latest guidelines on teacher training?",
      "mode": "deep_think",
      "internet_enabled": true
    }'
    ```
-   **Example Response**:
    ```json
    {
      "answer": "The latest guidelines emphasize continuous professional development...",
      "citations": [
        {
          "docId": "some-document-id",
          "page": 2,
          "span": "teacher training programs",
          "source": "Education Policy 2023",
          "vertical": "policy",
          "url": null
        }
      ],
      "processing_trace": {
        "language": "en",
        "retrieval": {
          "verticals_searched": ["policy", "internet"],
          "processing_time": 1.23,
          "total_candidates": 100,
          "final_count": 10,
          "cache_hits": 0,
          "rewrites_count": 1
        },
        "kg_traversal": "v3_multi_hop_retrieval",
        "controller_iterations": 1,
        "steps": ["step 1", "step 2"]
      },
      "risk_assessment": "low",
      "performance_metrics": {
        "total_time": 2.34,
        "retrieval_time": 1.23,
        "answer_time": 1.11,
        "cache_hit_rate": 0,
        "verticals_searched": 2,
        "rewrites_generated": 1,
        "candidates_processed": 100,
        "parallel_processing": true
      }
    }
    ```
-   **Dependencies**: This endpoint relies on the `RetrievalEngine` for retrieving documents and the `AnswerGenerator` for generating the final answer.

### 3.3. `/v3/query_with_files`

-   **Purpose**: Handles queries that include file uploads for additional context.
-   **Method and URL**: `POST /v3/query_with_files`
-   **Request Schema**: Multipart form data with the following fields:
    -   `query`: `string`
    -   `mode`: `string`
    -   `internet_enabled`: `boolean`
    -   `files`: one or more `File` objects
    -   `conversation_history`: `string` (JSON string)
-   **Response Schema**: Same as `/v3/query`.
-   **Example Request**:
    ```bash
    curl -X POST "http://localhost:8000/v3/query_with_files" \
      -F "query=Summarize the key points in the attached document regarding student assessments." \
      -F "mode=qa" \
      -F "internet_enabled=false" \
      -F "files=@/path/to/your/document.pdf"
    ```
-   **Example Response**: See `/v3/query`.
-   **Dependencies**: This endpoint uses the `FileHandler` to process uploaded files, the `RetrievalEngine` to retrieve relevant documents, and the `AnswerGenerator` to generate the answer.

## 4. Legacy Answer Generation

The legacy answer generation system is located in `retrieval/answer_generator.py`. It is responsible for generating the final answer based on the retrieved context.

-   **Backend Integration**: The backend's `/v3/query` and `/v3/query_with_files` endpoints call the `answer_generator.generate` method to produce the final answer.
-   **Inputs**: The `generate` method expects the following inputs:
    -   `query`: The user's query.
    -   `results`: A list of retrieved documents.
    -   `mode`: The query mode (`qa`, `deep_think`, or `brainstorm`).
    -   `external_context`: Text extracted from any uploaded files.
    -   `conversation_history`: The user's conversation history.
-   **Outputs**: The `generate` method returns a dictionary with the following keys:
    -   `answer`: The generated answer.
    -   `citations`: A list of citations used in the answer.
    -   `bibliography`: A list of all the documents that were considered.
    -   `confidence`: A score indicating the confidence in the answer.

## 5. Error Handling

-   **400 Bad Request**: This error is returned if the request is malformed. For example, if the `mode` in a query is not one of the valid options (`qa`, `deep_think`, or `brainstorm`), or if more than 3 files are uploaded at once.
    -   **Response Shape**:
        ```json
        {
          "detail": "string"
        }
        ```
-   **500 Internal Server Error**: This error is returned for any unhandled exceptions that occur during the processing of a request.
    -   **Response Shape**:
        ```json
        {
          "detail": "string"
        }
        ```
