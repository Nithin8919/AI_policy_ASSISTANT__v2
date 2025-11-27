"""
FastAPI Server for AP Policy Assistant v2
==========================================
Now with internet integration via query orchestrator.
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

# Add modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), "retrieval"))
sys.path.append(os.path.dirname(__file__))

from retrieval.router import RetrievalRouter
from retrieval.answer_generator import get_answer_generator
from retrieval.config.settings import validate_config

# NEW: Import orchestrator
from query_orchestrator import get_query_orchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
retrieval_router = None
answer_generator = None
query_orchestrator = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    global retrieval_router, answer_generator, query_orchestrator
    
    try:
        logger.info("🚀 Initializing AP Policy Assistant API v2...")
        
        # Validate config
        validate_config(allow_missing_llm=True)
        logger.info("✅ Configuration validated")
        
        # Initialize retrieval system
        retrieval_router = RetrievalRouter()
        logger.info("✅ Retrieval router initialized")
        
        # Initialize answer generator
        answer_generator = get_answer_generator()
        logger.info("✅ Answer generator initialized")
        
        # NEW: Initialize query orchestrator
        query_orchestrator = get_query_orchestrator(retrieval_router)
        logger.info("✅ Query orchestrator initialized")
        
        logger.info("🎉 AP Policy Assistant API v2 ready!")
        logger.info("   - Local RAG: ✓")
        logger.info("   - Internet: ✓")
        logger.info("   - Orchestration: ✓")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize API: {e}")
        raise
    finally:
        logger.info("🛑 Shutting down AP Policy Assistant API...")

# Create FastAPI app
app = FastAPI(
    title="AP Policy Assistant API v2",
    description="Backend API with Internet Integration",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class QueryRequest(BaseModel):
    query: str = Field(..., description="User query")
    simulate_failure: bool = Field(False, description="Simulate failure for testing")
    mode: str = Field("qa", description="Query mode: qa, deep_think, or brainstorm")
    use_internet: bool = Field(False, description="Enable internet search")  # NEW

class Citation(BaseModel):
    docId: str
    page: int
    span: str
    source_type: str = "local"  # NEW: local, internet, theory

class RetrievalResult(BaseModel):
    dense: List[str]
    sparse: List[str]

class ProcessingTrace(BaseModel):
    language: str
    retrieval: RetrievalResult
    kg_traversal: str
    controller_iterations: int
    sources_used: List[str] = []  # NEW: which sources were queried
    orchestration_time: float = 0.0  # NEW

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

# API Routes
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AP Policy Assistant API v2",
        "status": "running",
        "version": "2.0.0",
        "features": ["local_rag", "internet_search", "orchestration"]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "AP Policy Assistant API v2 is running",
        "services": {
            "retrieval": "healthy" if retrieval_router else "not_initialized",
            "orchestrator": "healthy" if query_orchestrator else "not_initialized",
            "answer_generator": "healthy" if answer_generator else "not_initialized"
        }
    }

@app.post("/v1/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest):
    """
    Main query endpoint with orchestration.
    Now supports internet toggle!
    """
    try:
        logger.info(f"📝 Query: '{request.query}' (mode={request.mode}, internet={request.use_internet})")
        
        # Simulate failure if requested
        if request.simulate_failure:
            raise HTTPException(status_code=500, detail="Simulated failure")
        
        # Validate mode
        valid_modes = ["qa", "deep_think", "brainstorm"]
        if request.mode not in valid_modes:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid mode. Must be one of: {valid_modes}"
            )
        
        # NEW: Use orchestrator instead of direct retrieval
        logger.info("🎯 Using orchestrator for multi-source retrieval...")
        
        orchestration_response = query_orchestrator.orchestrate(
            query=request.query,
            mode=request.mode,
            internet_toggle=request.use_internet
        )
        
        if not orchestration_response.get("success"):
            error_msg = orchestration_response.get("error", "Orchestration failed")
            logger.error(f"❌ Orchestration failed: {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)
        
        # Get merged results
        results = orchestration_response.get("results", [])
        decision = orchestration_response.get("decision", {})
        metadata = orchestration_response.get("metadata", {})
        
        logger.info(f"📊 Retrieved {len(results)} total results from: {metadata.get('sources', [])}")
        
        # Generate answer using fusion prompt
        logger.info("💭 Generating answer with multi-source context...")
        
        # Use the fusion prompt built by orchestrator
        fusion_prompt = orchestration_response.get("fusion_prompt", "")
        
        answer_response = answer_generator.generate(
            query=request.query,
            results=results,
            mode=request.mode,
            max_context_chunks=len(results),
            custom_prompt=fusion_prompt  # Pass fusion prompt if supported
        )
        
        # Format citations with source types
        citations = []
        for citation_num in answer_response.get("citations", []):
            try:
                result_idx = int(citation_num) - 1
                if 0 <= result_idx < len(results):
                    result = results[result_idx]
                    source_type = result.get("source_type", "local")
                    
                    citations.append(Citation(
                        docId=result.get("chunk_id", f"doc_{citation_num}"),
                        page=1,
                        span=result.get("text", "")[:100] + "...",
                        source_type=source_type
                    ))
            except (ValueError, IndexError):
                continue
        
        # Create processing trace with orchestration info
        processing_trace = ProcessingTrace(
            language="en",
            retrieval=RetrievalResult(
                dense=[r.get("chunk_id", "") for r in results[:3]],
                sparse=[r.get("chunk_id", "") for r in results[3:6]]
            ),
            kg_traversal="multi_source",
            controller_iterations=1,
            sources_used=metadata.get("sources", []),
            orchestration_time=metadata.get("orchestration_time", 0.0)
        )
        
        response = QueryResponse(
            answer=answer_response.get("answer", "No answer generated"),
            citations=citations,
            processing_trace=processing_trace,
            risk_assessment="low"
        )
        
        logger.info(f"✅ Query complete: {len(response.answer)} chars, "
                   f"{len(citations)} citations, "
                   f"sources: {metadata.get('sources', [])}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Query error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.get("/v1/status", response_model=SystemStatusResponse)
async def get_system_status():
    """Get detailed system status"""
    try:
        from datetime import datetime
        
        # Check internet service
        internet_status = "not_configured"
        try:
            from internet_service import get_internet_client
            client = get_internet_client()
            health = client.health_check()
            internet_status = health.get("status", "unknown")
        except:
            pass
        
        services = {
            "retrieval_system": "healthy" if retrieval_router else "not_initialized",
            "answer_generator": "healthy" if answer_generator else "not_initialized",
            "orchestrator": "healthy" if query_orchestrator else "not_initialized",
            "internet_service": internet_status,
            "database": "connected",
            "gemini_api": "configured" if os.getenv("GEMINI_API_KEY") else "not_configured"
        }
        
        status = "healthy" if all(
            s in ["healthy", "connected", "configured"] 
            for s in services.values()
        ) else "degraded"
        
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
        return {
            "id": document_id,
            "title": f"Document {document_id}",
            "content": "Document content...",
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
        logger.info(f"📝 Feedback: rating={request.rating}")
        
        return {
            "message": "Feedback submitted",
            "id": "feedback_123"
        }
    except Exception as e:
        logger.error(f"❌ Feedback error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    
    logger.info(f"🚀 Starting AP Policy Assistant API v2 on 0.0.0.0:{port}")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )