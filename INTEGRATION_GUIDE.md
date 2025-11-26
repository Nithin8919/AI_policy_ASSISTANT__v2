# AP Policy Assistant Integration Guide

## Quick Start

### 1. Set Environment Variables
```bash
export GEMINI_API_KEY=your_gemini_api_key_here
```

### 2. Start the API Server
```bash
chmod +x start_api.sh
./start_api.sh
```
The API will run on `http://0.0.0.0:8000`

### 3. Start the Frontend
```bash
chmod +x start_frontend.sh
./start_frontend.sh
```
The frontend will run on `http://localhost:3000`

## Integration Details

### API Endpoints Implemented

1. **POST /v1/query** - Main query processing
   - Input: `{query: string, mode: "qa"|"deep_think"|"brainstorm", simulate_failure?: boolean}`
   - Output: Answer with citations and processing trace

2. **GET /v1/status** - System health check

3. **GET /v1/document/{id}** - Document retrieval

4. **POST /v1/feedback** - User feedback submission

5. **POST /v1/scrape** - Web scraping (placeholder)

### Frontend Updates Made

1. **Query Modes**: Only shows qa, deep_think, brainstorm modes
2. **Model Selection**: Removed (only uses Gemini backend)
3. **Citations Display**: Added prominent citation boxes for all responses
4. **API Integration**: Updated to use new endpoint structure

### Key Features

- **Fast & Seamless**: Direct integration between frontend and retrieval system
- **Proper Citations**: Every response shows source documents with citations
- **Multiple Modes**: 
  - QA: Quick factual answers
  - Deep Think: Detailed analysis with reasoning
  - Brainstorm: Creative policy suggestions
- **Error Handling**: Graceful error handling and user feedback

## Network Configuration

The API server binds to `0.0.0.0:8000` to prevent localhost/port binding issues that occurred previously. The frontend connects via `http://localhost:8000`.

## Environment Variables

- `GEMINI_API_KEY` or `GOOGLE_API_KEY`: Required for answer generation
- `PORT`: API server port (default: 8000)
- `NEXT_PUBLIC_API_URL`: Frontend API connection URL (default: http://localhost:8000)

## Troubleshooting

1. **API Connection Issues**: Ensure API is running on 0.0.0.0:8000
2. **Missing Citations**: Check GEMINI_API_KEY is set correctly
3. **Frontend Errors**: Verify NEXT_PUBLIC_API_URL points to running API
4. **Retrieval Issues**: Check Qdrant database connection and data

## Testing the Integration

1. Start both API and frontend
2. Go to http://localhost:3000/chat
3. Select a query mode (QA, Deep Think, or Brainstorm)
4. Ask: "What are the key education policies in AP?"
5. Verify you get an answer with citations displayed

The integration is now complete and ready for use!