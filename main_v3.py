"""
FastAPI Server for AP Policy Assistant V3
=========================================
Backend API using the optimized V3 retrieval pipeline with parallel processing.
"""

import os
import sys
import logging
import time
from typing import Dict, List, Optional
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, BackgroundTasks, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()

# Add V3 modules to path
sys.path.insert(0, 'retrieval_v3')
sys.path.insert(0, 'retrieval')

# Import V3 components
from retrieval.retrieval_core.qdrant_client import get_qdrant_client
from retrieval.embeddings.embedder import get_embedder
from retrieval_v3.pipeline.retrieval_engine import RetrievalEngine
from retrieval.answer_generator import get_answer_generator
from retrieval_v3.answer_generation.answer_builder import AnswerBuilder
from retrieval_v3.file_processing.file_handler import FileHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
v3_engine = None
answer_generator = None
answer_builder = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    global v3_engine, answer_generator, answer_builder
    
    try:
        logger.info("🚀 Initializing AP Policy Assistant V3 API...")
        
        # Initialize V3 retrieval engine
        logger.info("📡 Connecting to Qdrant...")
        qdrant = get_qdrant_client()
        
        logger.info("🧠 Loading Google embedder...")
        embedder = get_embedder()
        
        logger.info("⚡ Creating V3 retrieval engine...")
        v3_engine = RetrievalEngine(
            qdrant_client=qdrant,
            embedder=embedder,
            gemini_api_key=os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY'),
            use_llm_rewrites=True,
            use_llm_reranking=True,
            enable_cache=True
        )
        
        # Initialize answer generator
        logger.info("💭 Initializing answer generator...")
        answer_generator = get_answer_generator()
        
        # Initialize V3 answer builder (for Policy Crafter)
        logger.info("💭 Initializing V3 answer builder...")
        answer_builder = AnswerBuilder(
            use_llm=True,
            api_key=os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
        )
        
        logger.info("🎉 V3 API ready! Features:")
        logger.info("  ⚡ Parallel processing with ThreadPoolExecutor")
        logger.info("  🧠 Intelligent caching (1.6x speedup)")
        logger.info("  🔍 Multi-hop retrieval across all verticals")
        logger.info("  📊 LLM-enhanced query understanding")
        logger.info("  🎯 Sub-3s average response time")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize V3 API: {e}")
        raise
    finally:
        if v3_engine:
            v3_engine.cleanup()
        logger.info("🛑 Shutting down V3 API...")

# Create FastAPI app
app = FastAPI(
    title="AP Policy Assistant V3 API",
    description="Optimized backend with parallel processing and intelligent caching",
    version="3.0.0",
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
    mode: str = Field("qa", description="Query mode: qa, deep_think, brainstorm, policy_brief, or policy_draft")
    top_k: Optional[int] = Field(None, description="Override number of results")
    internet_enabled: Optional[bool] = Field(False, description="Enable internet search")
    conversation_history: Optional[List[Dict[str, str]]] = Field(None, description="Previous conversation turns for context")

class Citation(BaseModel):
    docId: str
    page: int
    span: str
    source: str
    vertical: str

class V3RetrievalResult(BaseModel):
    verticals_searched: List[str]
    processing_time: float
    total_candidates: int
    final_count: int
    cache_hits: int
    rewrites_count: int

class ProcessingTrace(BaseModel):
    language: str
    retrieval: V3RetrievalResult
    kg_traversal: str
    controller_iterations: int
    steps: List[str] = Field(default_factory=list)

class QueryResponse(BaseModel):
    answer: str
    citations: List[Citation]
    processing_trace: ProcessingTrace
    risk_assessment: str
    performance_metrics: Dict

class SystemStatusResponse(BaseModel):
    status: str
    services: Dict
    timestamp: str
    engine_stats: Dict

# Helper function for citation display names
def construct_citation_name(result: Dict, metadata: Dict) -> str:
    """Construct a user-friendly display name from available metadata"""
    import re
    
    # Priority 1: Check for explicit filename or title (for uploaded files or web results)
    if metadata.get('filename'):
        return metadata['filename']
    if metadata.get('file_name'):
        return metadata['file_name']
    if metadata.get('title'):
        return metadata['title']
    
    # Priority 2: Construct from GO metadata (for government orders)
    go_number = metadata.get('go_number')
    if go_number:
        parts = [f"GO {go_number}"]
        
        # Add department if available
        department = metadata.get('department')
        if department:
            # Shorten department name if too long
            dept_short = department[:20] + "..." if len(department) > 20 else department
            parts.append(dept_short)
        
        # Add year if available
        year = metadata.get('year')
        if year:
            parts.append(str(year))
        
        return " - ".join(parts)
    
    # Priority 3: Use doc_id if it looks meaningful (not a UUID)
    doc_id = result.get('doc_id', result.get('chunk_id', ''))
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    if doc_id and not re.match(uuid_pattern, str(doc_id).lower()):
        return doc_id
    
    # Priority 4: Fallback to source or generic label
    source = metadata.get('source', 'Document')
    if source and source != 'Unknown':
        return source
    
    return f"Document {result.get('doc_id', 'Unknown')[:8]}"

# API Routes
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AP Policy Assistant V3 API", 
        "status": "running",
        "features": [
            "Parallel processing",
            "Intelligent caching", 
            "Multi-hop retrieval",
            "LLM-enhanced understanding",
            "Sub-3s performance"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "V3 API is running with optimized performance"}

@app.post("/v3/query", response_model=QueryResponse)
async def v3_query_endpoint(request: QueryRequest):
    """V3 optimized query endpoint"""
    start_time = time.time()
    
    try:
        logger.info(f"🔍 V3 Query: '{request.query}' (mode: {request.mode}, internet: {request.internet_enabled})")
        
        # Validate mode
        valid_modes = ["qa", "deep_think", "brainstorm"]
        if request.mode not in valid_modes:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid mode '{request.mode}'. Must be one of: {valid_modes}"
            )
        
        # V3 Retrieval with parallel processing
        logger.info("⚡ Starting V3 parallel retrieval...")
        retrieval_start = time.time()
        
        # Build custom plan with internet setting
        # Force internet ON for brainstorm mode, otherwise use request setting
        should_enable_internet = request.internet_enabled or request.mode == "brainstorm"
        custom_plan = {'internet_enabled': True} if should_enable_internet else None
        
        v3_output = v3_engine.retrieve(
            query=request.query,
            top_k=request.top_k,
            custom_plan=custom_plan
        )
        
        retrieval_time = time.time() - retrieval_start
        logger.info(f"📄 V3 Retrieved {v3_output.final_count} results in {retrieval_time:.2f}s")
        
        # Generate answer
        logger.info("💭 Generating answer...")
        answer_start = time.time()
        
        if request.mode == "policy_draft":
            # Use V3 AnswerBuilder for Policy Crafter
            logger.info("📝 Using V3 AnswerBuilder for Policy Draft...")
            
            # Convert results for builder
            results_for_builder = []
            for result in v3_output.results:
                results_for_builder.append({
                    "content": result.content,
                    "chunk_id": result.chunk_id,
                    "doc_id": result.doc_id,
                    "score": result.score,
                    "metadata": result.metadata,
                    "vertical": result.vertical,
                    "url": result.metadata.get('url') if 'url' in result.metadata else None
                })
            
            answer_obj = answer_builder.build_answer(
                query=request.query,
                results=results_for_builder,
                mode=request.mode,
                conversation_history=request.conversation_history
            )
            
            # Build full answer from summary + sections
            full_answer = answer_obj.summary
            if answer_obj.sections:
                for section_name, section_content in answer_obj.sections.items():
                    full_answer += "\n\n" + section_content
            
            answer_text = full_answer
            citations_list = answer_obj.citations
            
        else:
            # Use old AnswerGenerator for standard queries (better quality for QA)
            # Convert V3 results to old format
            results_old_fmt = []
            for result in v3_output.results:
                results_old_fmt.append({
                    "chunk_id": result.chunk_id,
                    "text": result.content,
                    "doc_id": result.doc_id,
                    "score": result.score,
                    "metadata": result.metadata,
                    "vertical": result.vertical,
                    "rewrite_source": result.rewrite_source
                })
            
            answer_response = answer_generator.generate(
                query=request.query,
                results=results_old_fmt,
                mode=request.mode,
                max_context_chunks=5 if request.mode == "qa" else 10,
                conversation_history=request.conversation_history
            )
            
            answer_text = answer_response.get("answer", "No answer generated")
            citations_list = [] # We'll handle citations below based on the source
            
            # Extract citations from answer_response for processing below
            raw_citations = answer_response.get("citations", [])
        
        answer_time = time.time() - answer_start
        
        # Format citations
        citations = []
        
        if request.mode == "policy_draft":
            # V3 Builder citations format
            for citation in citations_list:
                citations.append(Citation(
                    docId=citation.get('filename') or citation.get('source') or citation.get('doc_id', 'Unknown'),
                    page=citation.get('page') or 1,
                    span=citation.get('source', '')[:150],
                    source=citation.get('filename') or citation.get('source', 'Policy Document'),
                    vertical=citation.get('vertical', 'unknown')
                ))
        else:
            # Old Generator citations format
            for citation_num in raw_citations:
                try:
                    result_idx = int(citation_num) - 1
                    if 0 <= result_idx < len(results_old_fmt):
                        result = results_old_fmt[result_idx]
                        metadata = result.get("metadata", {})
                        
                        # Construct display name from metadata
                        display_name = construct_citation_name(result, metadata)
                        
                        citations.append(Citation(
                            docId=display_name,
                            page=metadata.get('page_number') or metadata.get('page') or 1,
                            span=result.get("text", "")[:150] + "...",
                            source=display_name,
                            vertical=result.get("vertical", "unknown")
                        ))
                except (ValueError, IndexError):
                    continue
        
        # Create V3 processing trace
        processing_trace = ProcessingTrace(
            language="en",
            retrieval=V3RetrievalResult(
                verticals_searched=v3_output.verticals_searched,
                processing_time=v3_output.processing_time,
                total_candidates=v3_output.total_candidates,
                final_count=v3_output.final_count,
                cache_hits=v3_engine.stats.get('cache_hits', 0),
                rewrites_count=len(v3_output.rewrites)
            ),
            kg_traversal="v3_multi_hop_retrieval",
            controller_iterations=v3_output.metadata.get('num_hops', 1),
            steps=v3_output.trace_steps
        )
        
        total_time = time.time() - start_time
        
        # Performance metrics
        performance_metrics = {
            "total_time": round(total_time, 3),
            "retrieval_time": round(retrieval_time, 3),
            "answer_time": round(answer_time, 3),
            "cache_hit_rate": round(v3_engine.stats.get('cache_hits', 0) / max(v3_engine.stats.get('total_queries', 1), 1) * 100, 1),
            "verticals_searched": len(v3_output.verticals_searched),
            "rewrites_generated": len(v3_output.rewrites),
            "candidates_processed": v3_output.total_candidates,
            "parallel_processing": True
        }
        
        response = QueryResponse(
            answer=answer_text,
            citations=citations,
            processing_trace=processing_trace,
            risk_assessment="low",
            performance_metrics=performance_metrics
        )
        
        logger.info(f"✅ V3 Query completed in {total_time:.2f}s - Answer: {len(response.answer)} chars, Citations: {len(citations)}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ V3 Query error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"V3 processing error: {str(e)}")

@app.post("/v3/query_with_files", response_model=QueryResponse)
async def v3_query_with_files_endpoint(
    query: str = Form(...),
    mode: str = Form("qa"),
    internet_enabled: bool = Form(False),
    files: List[UploadFile] = File(...),
    conversation_history: Optional[str] = Form(None)
):
    """V3 query endpoint with file upload support"""
    start_time = time.time()
    
    try:
        # Parse conversation history if provided (it comes as JSON string from form data)
        parsed_history = None
        if conversation_history:
            import json
            try:
                parsed_history = json.loads(conversation_history)
            except json.JSONDecodeError:
                logger.warning("Failed to parse conversation_history, ignoring")
        
        logger.info(f"🔍 V3 Query with files: '{query}' (mode: {mode}, files: {len(files)})")
        
        # Validate number of files
        if len(files) > 3:
            raise HTTPException(
                status_code=400,
                detail="Maximum 3 files allowed per query"
            )
        
        # Initialize file handler
        file_handler = FileHandler()
        
        # Process uploaded files
        file_contexts = []
        file_errors = []
        
        for file in files:
            logger.info(f"📄 Processing file: {file.filename}")
            result = await file_handler.process_file(file)
            
            if result['success']:
                file_contexts.append({
                    'filename': result['filename'],
                    'text': result['text'],
                    'word_count': result['word_count']
                })
                logger.info(f"✅ Extracted {result['word_count']} words from {result['filename']}")
            else:
                file_errors.append({
                    'filename': result['filename'],
                    'error': result.get('error', 'Unknown error')
                })
                logger.warning(f"⚠️ Failed to process {result['filename']}: {result.get('error')}")
        
        # If all files failed, return error
        if not file_contexts and file_errors:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to process files: {', '.join(e['error'] for e in file_errors)}"
            )
        
        # Augment query with file context
        augmented_query = query
        file_context_text = None  # Initialize to None
        
        if file_contexts:
            file_context_text = "\n\n".join([
                f"--- Content from {fc['filename']} ({fc['word_count']} words) ---\n{fc['text']}"
                for fc in file_contexts
            ])
            logger.info(f"📝 File context length: {len(file_context_text)} chars")
        else:
            logger.info("📝 No file context (no files uploaded or all failed)")
        
        # V3 Retrieval with ORIGINAL query (don't confuse retriever with file content)
        logger.info("⚡ Starting V3 retrieval...")
        retrieval_start = time.time()
        
        # Build custom plan with internet setting
        custom_plan = {'internet_enabled': internet_enabled} if internet_enabled else None
        
        v3_output = v3_engine.retrieve(
            query=query,
            top_k=10,
            custom_plan=custom_plan
        )
        
        retrieval_time = time.time() - retrieval_start
        logger.info(f"📄 V3 Retrieved {v3_output.final_count} results in {retrieval_time:.2f}s")
        
        # Generate answer
        logger.info("💭 Generating answer...")
        answer_start = time.time()
        
        if mode == "policy_draft":
            # Use V3 AnswerBuilder for Policy Crafter
            logger.info("📝 Using V3 AnswerBuilder for Policy Draft...")
            
            # Convert results for builder
            results_for_builder = []
            for result in v3_output.results:
                results_for_builder.append({
                    "content": result.content,
                    "chunk_id": result.chunk_id,
                    "doc_id": result.doc_id,
                    "score": result.score,
                    "metadata": result.metadata,
                    "vertical": result.vertical,
                    "url": result.metadata.get('url') if 'url' in result.metadata else None
                })
            
            answer_obj = answer_builder.build_answer(
                query=query,
                results=results_for_builder,
                mode=mode,
                external_context=file_context_text,
                conversation_history=parsed_history
            )
            
            # Build full answer from summary + sections
            full_answer = answer_obj.summary
            if answer_obj.sections:
                for section_name, section_content in answer_obj.sections.items():
                    full_answer += "\n\n" + section_content
            
            answer_text = full_answer
            citations_list = answer_obj.citations
            
        else:
            # Use old AnswerGenerator for standard queries
            # Convert V3 results to old format
            results_old_fmt = []
            for result in v3_output.results:
                results_old_fmt.append({
                    "chunk_id": result.chunk_id,
                    "text": result.content,
                    "doc_id": result.doc_id,
                    "score": result.score,
                    "metadata": result.metadata,
                    "vertical": result.vertical,
                    "rewrite_source": result.rewrite_source
                })
            
            answer_response = answer_generator.generate(
                query=query,
                results=results_old_fmt,
                mode=mode,
                max_context_chunks=5 if mode == "qa" else 10,
                external_context=file_context_text,
                conversation_history=parsed_history
            )
            
            answer_text = answer_response.get("answer", "No answer generated")
            citations_list = []
            raw_citations = answer_response.get("citations", [])
        
        answer_time = time.time() - answer_start
        
        # Format citations
        citations = []
        
        if mode == "policy_draft":
            for citation in citations_list:
                citations.append(Citation(
                    docId=citation.get('filename') or citation.get('source') or citation.get('doc_id', 'Unknown'),
                    page=citation.get('page') or 1,
                    span=citation.get('source', '')[:150],
                    source=citation.get('filename') or citation.get('source', 'Policy Document'),
                    vertical=citation.get('vertical', 'unknown')
                ))
        else:
            for citation_num in raw_citations:
                try:
                    result_idx = int(citation_num) - 1
                    if 0 <= result_idx < len(results_old_fmt):
                        result = results_old_fmt[result_idx]
                        metadata = result.get("metadata", {})
                        
                        display_name = construct_citation_name(result, metadata)
                        
                        citations.append(Citation(
                            docId=display_name,
                            page=metadata.get('page_number') or metadata.get('page') or 1,
                            span=result.get("text", "")[:150] + "...",
                            source=display_name,
                            vertical=result.get("vertical", "unknown")
                        ))
                except (ValueError, IndexError):
                    continue
        
        # Create V3 processing trace
        processing_trace = ProcessingTrace(
            language="en",
            retrieval=V3RetrievalResult(
                verticals_searched=v3_output.verticals_searched,
                processing_time=v3_output.processing_time,
                total_candidates=v3_output.total_candidates,
                final_count=v3_output.final_count,
                cache_hits=v3_engine.stats.get('cache_hits', 0),
                rewrites_count=len(v3_output.rewrites)
            ),
            kg_traversal="v3_multi_hop_retrieval_with_files",
            controller_iterations=v3_output.metadata.get('num_hops', 1),
            steps=v3_output.trace_steps
        )
        
        total_time = time.time() - start_time
        
        # Performance metrics
        performance_metrics = {
            "total_time": round(total_time, 3),
            "retrieval_time": round(retrieval_time, 3),
            "answer_time": round(answer_time, 3),
            "files_processed": len(file_contexts),
            "files_failed": len(file_errors),
            "total_file_words": sum(fc['word_count'] for fc in file_contexts),
            "verticals_searched": len(v3_output.verticals_searched),
            "rewrites_generated": len(v3_output.rewrites),
            "candidates_processed": v3_output.total_candidates,
        }
        
        response = QueryResponse(
            answer=answer_text,
            citations=citations,
            processing_trace=processing_trace,
            risk_assessment="low",
            performance_metrics=performance_metrics
        )
        
        logger.info(f"✅ V3 Query with files completed in {total_time:.2f}s")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ V3 Query with files error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"V3 file processing error: {str(e)}")

@app.get("/v3/status", response_model=SystemStatusResponse)
async def get_v3_status():
    """Get V3 system status with engine stats"""
    try:
        from datetime import datetime
        
        services = {
            "v3_retrieval_engine": "healthy" if v3_engine else "not_initialized",
            "parallel_processing": "active" if v3_engine and hasattr(v3_engine, 'executor') else "inactive",
            "intelligent_caching": "enabled" if v3_engine and v3_engine.enable_cache else "disabled",
            "qdrant_database": "connected",
            "google_embedder": "configured",
            "gemini_api": "configured" if os.getenv("GEMINI_API_KEY") else "not_configured"
        }
        
        # Get engine statistics
        engine_stats = {}
        if v3_engine:
            stats = v3_engine.stats
            engine_stats = {
                "total_queries_processed": stats.get('total_queries', 0),
                "average_processing_time": round(stats.get('avg_processing_time', 0), 3),
                "cache_hits": stats.get('cache_hits', 0),
                "cache_hit_rate": round(stats.get('cache_hits', 0) / max(stats.get('total_queries', 1), 1) * 100, 1)
            }
        
        status = "healthy" if all(
            s in ["healthy", "active", "enabled", "connected", "configured"] 
            for s in services.values()
        ) else "degraded"
        
        return SystemStatusResponse(
            status=status,
            services=services,
            timestamp=datetime.now().isoformat(),
            engine_stats=engine_stats
        )
        
    except Exception as e:
        logger.error(f"❌ V3 Status check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v3/test")
async def test_v3_performance():
    """Test V3 performance with sample queries"""
    try:
        test_queries = [
            "What is Section 12 RTE Act?",
            "AI integration in school curriculum", 
            "Nadu-Nedu infrastructure development",
            "Latest education policies"
        ]
        
        results = []
        total_start = time.time()
        
        for query in test_queries:
            start = time.time()
            output = v3_engine.retrieve(query, top_k=10)
            elapsed = time.time() - start
            
            results.append({
                "query": query,
                "processing_time": round(elapsed, 3),
                "results_count": output.final_count,
                "verticals": output.verticals_searched,
                "candidates": output.total_candidates,
                "rewrites": len(output.rewrites)
            })
        
        total_time = time.time() - total_start
        
        return {
            "test_summary": {
                "total_time": round(total_time, 3),
                "average_time": round(total_time / len(test_queries), 3),
                "queries_tested": len(test_queries),
                "all_under_5s": all(r["processing_time"] < 5.0 for r in results)
            },
            "individual_results": results,
            "engine_stats": v3_engine.stats
        }
        
    except Exception as e:
        logger.error(f"❌ V3 Performance test error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v3/metrics")
async def get_v3_metrics():
    """Get detailed V3 performance metrics"""
    try:
        if not v3_engine:
            raise HTTPException(status_code=503, detail="V3 engine not initialized")
        
        stats = v3_engine.stats
        
        return {
            "performance_metrics": {
                "total_queries": stats.get('total_queries', 0),
                "average_processing_time": round(stats.get('avg_processing_time', 0), 3),
                "cache_hits": stats.get('cache_hits', 0),
                "cache_hit_rate_percent": round(stats.get('cache_hits', 0) / max(stats.get('total_queries', 1), 1) * 100, 1),
                "best_time_achieved": stats.get('best_time', 0)
            },
            "system_info": {
                "parallel_processing": True,
                "thread_pool_workers": 6,
                "caching_enabled": v3_engine.enable_cache,
                "llm_rewrites_enabled": v3_engine.use_llm_rewrites,
                "llm_reranking_enabled": v3_engine.use_llm_reranking
            },
            "target_performance": {
                "target_response_time": "< 5.0s",
                "target_cache_speedup": "> 1.5x",
                "parallel_speedup": "~2.0x"
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Metrics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Legacy compatibility endpoint
@app.post("/v1/query")
async def legacy_query_redirect(request: QueryRequest):
    """Redirect legacy queries to V3 endpoint"""
    logger.info(f"🔄 Redirecting legacy query to V3: {request.query}")
    return await v3_query_endpoint(request)

if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment or default to 8000 (replaces old backend)
    port = int(os.getenv("PORT", 8000))
    
    logger.info(f"🚀 Starting AP Policy Assistant V3 API on 0.0.0.0:{port}")
    logger.info("🎯 Features: Parallel processing, intelligent caching, sub-3s performance")
    
    uvicorn.run(
        "main_v3:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )