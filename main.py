"""
FastAPI Server for AP Policy Assistant
=====================================
Seamless integration between frontend and retrieval system.
"""

import os
import sys
import logging
from typing import Dict, List, Optional
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()

# Add retrieval module to path
sys.path.append(os.path.join(os.path.dirname(__file__), "retrieval"))

from retrieval.router import RetrievalRouter
from retrieval.answer_generator import get_answer_generator
from retrieval.config.settings import validate_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
retrieval_router = None
answer_generator = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    global retrieval_router, answer_generator
    
    try:
        logger.info("🚀 Initializing AP Policy Assistant API...")
        
        # Validate config (skip LLM check since we use Gemini directly)
        validate_config(allow_missing_llm=True)
        logger.info("✅ Configuration validated")
        
        # Initialize retrieval system
        retrieval_router = RetrievalRouter()
        logger.info("✅ Retrieval router initialized")
        
        # Initialize answer generator
        answer_generator = get_answer_generator()
        logger.info("✅ Answer generator initialized")
        
        logger.info("🎉 AP Policy Assistant API ready!")
        yield
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize API: {e}")
        raise
    finally:
        logger.info("🛑 Shutting down AP Policy Assistant API...")

# Create FastAPI app
app = FastAPI(
    title="AP Policy Assistant API",
    description="Backend API for Andhra Pradesh Education Policy Assistant",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware - Allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class QueryRequest(BaseModel):
    query: str = Field(..., description="User query")
    simulate_failure: bool = Field(False, description="Simulate failure for testing")
    mode: str = Field("qa", description="Query mode: qa, deep_think, or brainstorm")

class Citation(BaseModel):
    docId: str
    page: int
    span: str

class RetrievalResult(BaseModel):
    dense: List[str]
    sparse: List[str]

class ProcessingTrace(BaseModel):
    language: str
    retrieval: RetrievalResult
    kg_traversal: str
    controller_iterations: int

class QueryResponse(BaseModel):
    answer: str
    citations: List[Citation]
    processing_trace: ProcessingTrace
    risk_assessment: str

class SystemStatusResponse(BaseModel):
    status: str
    services: Dict
    timestamp: str

class FeedbackRequest(BaseModel):
    query: str
    response: str
    rating: int = Field(..., ge=1, le=5)
    comments: Optional[str] = None

class ScrapeRequest(BaseModel):
    url: str
    method: str = "auto"
    max_retries: int = 3

# API Routes
@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "AP Policy Assistant API", "status": "running"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "AP Policy Assistant API is running"}

@app.post("/v1/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest):
    """Main query endpoint"""
    try:
        logger.info(f"📝 Received query: '{request.query}' (mode: {request.mode})")
        
        # Simulate failure if requested
        if request.simulate_failure:
            raise HTTPException(status_code=500, detail="Simulated failure for testing")
        
        # Validate mode
        valid_modes = ["qa", "deep_think", "brainstorm"]
        if request.mode not in valid_modes:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid mode '{request.mode}'. Must be one of: {valid_modes}"
            )
        
        # Retrieve relevant documents
        logger.info(f"🔍 Starting retrieval with mode: {request.mode}")
        retrieval_response = retrieval_router.query(
            query=request.query,
            mode=request.mode
        )
        
        if not retrieval_response.get("success"):
            error_msg = retrieval_response.get("error", "Retrieval failed")
            logger.error(f"❌ Retrieval failed: {error_msg}")
            raise HTTPException(status_code=500, detail=f"Retrieval failed: {error_msg}")
        
        results = retrieval_response.get("results", [])
        logger.info(f"📄 Retrieved {len(results)} documents")
        
        # Generate answer with citations
        logger.info("💭 Generating answer...")
        answer_response = answer_generator.generate(
            query=request.query,
            results=results,
            mode=request.mode,
            max_context_chunks=5 if request.mode == "qa" else 10
        )
        
        # Format citations for frontend
        citations = []
        for citation_num in answer_response.get("citations", []):
            try:
                result_idx = int(citation_num) - 1
                if 0 <= result_idx < len(results):
                    result = results[result_idx]
                    citations.append(Citation(
                        docId=result.get("chunk_id", f"doc_{citation_num}"),
                        page=1,  # Default page
                        span=result.get("text", "")[:100] + "..."
                    ))
            except (ValueError, IndexError):
                continue
        
        # Create processing trace
        processing_trace = ProcessingTrace(
            language="en",
            retrieval=RetrievalResult(
                dense=[r.get("chunk_id", "") for r in results[:3]],
                sparse=[r.get("chunk_id", "") for r in results[3:6]]
            ),
            kg_traversal="policy_documents",
            controller_iterations=1
        )
        
        response = QueryResponse(
            answer=answer_response.get("answer", "No answer generated"),
            citations=citations,
            processing_trace=processing_trace,
            risk_assessment="low"
        )
        
        logger.info(f"✅ Query processed successfully. Answer length: {len(response.answer)}, Citations: {len(citations)}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Query processing error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/v1/status", response_model=SystemStatusResponse)
async def get_system_status():
    """Get system status"""
    try:
        from datetime import datetime
        
        services = {
            "retrieval_system": "healthy" if retrieval_router else "not_initialized",
            "answer_generator": "healthy" if answer_generator else "not_initialized",
            "database": "connected",  # Assume Qdrant is connected
            "gemini_api": "configured" if os.getenv("GEMINI_API_KEY") else "not_configured"
        }
        
        status = "healthy" if all(s == "healthy" or s == "connected" or s == "configured" for s in services.values()) else "degraded"
        
        return SystemStatusResponse(
            status=status,
            services=services,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"❌ Status check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/document/{document_id}")
async def get_document(document_id: str):
    """Get document by ID"""
    try:
        # This would typically query your document store
        # For now, return a placeholder
        return {
            "id": document_id,
            "title": f"Document {document_id}",
            "content": "Document content would be here...",
            "metadata": {
                "source": "AP Education Department",
                "type": "policy_document"
            }
        }
    except Exception as e:
        logger.error(f"❌ Document retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/feedback")
async def submit_feedback(request: FeedbackRequest):
    """Submit user feedback"""
    try:
        logger.info(f"📝 Feedback received: rating={request.rating}")
        
        # Store feedback (implement actual storage later)
        feedback_data = {
            "query": request.query,
            "response": request.response,
            "rating": request.rating,
            "comments": request.comments,
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
        return {"message": "Feedback submitted successfully", "id": "feedback_123"}
    except Exception as e:
        logger.error(f"❌ Feedback submission error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/scrape")
async def scrape_url(request: ScrapeRequest):
    """Web scraping endpoint (placeholder)"""
    try:
        logger.info(f"🌐 Scraping URL: {request.url}")
        
        # Placeholder implementation
        return {
            "url": request.url,
            "title": "Scraped Page Title",
            "content": "Scraped content would be here...",
            "metadata": {
                "method": request.method,
                "timestamp": "2024-01-01T00:00:00Z"
            }
        }
    except Exception as e:
        logger.error(f"❌ Scraping error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment or default to 8000
    port = int(os.getenv("PORT", 8000))
    
    logger.info(f"🚀 Starting AP Policy Assistant API on 0.0.0.0:{port}")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",  # Bind to all interfaces to prevent localhost issues
        port=port,
        reload=True,
        log_level="info"
    )