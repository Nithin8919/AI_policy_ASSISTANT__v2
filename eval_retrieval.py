"""
Retrieval Evaluation Script
===========================
Runs a set of golden queries against the V3 retrieval engine and computes metrics.
"""

import sys
import time
import logging
from typing import List, Dict
from dotenv import load_dotenv

# Setup paths
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Import retrieval system as proper package
import retrieval
from retrieval.retrieval_core.qdrant_client import get_qdrant_client
from retrieval.embeddings.embedder import get_embedder
from retrieval.config.settings import validate_config
from retrieval_v3.pipeline.retrieval_engine import RetrievalEngine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Golden Set Queries (Query -> Expected Keywords/DocTypes)
GOLDEN_QUERIES = [
    {
        "query": "G.O.MS.No.26 Dated 16-02-2019",
        "expected_text": ["G.O.MS.No.26", "16-02-2019", "amendment"],
        "type": "go_lookup"
    },
    {
        "query": "What is Section 12 of RTE Act?",
        "expected_text": ["Section 12", "Right to Education", "25%", "weaker section"],
        "type": "clause_lookup"
    },
    {
        "query": "Amma Vodi scheme eligibility",
        "expected_text": ["Amma Vodi", "eligibility", "mother", "poverty line"],
        "type": "scheme_lookup"
    },
    {
        "query": "Nadu Nedu infrastructure guidelines",
        "expected_text": ["Nadu Nedu", "infrastructure", "toilet", "drinking water"],
        "type": "infra_lookup"
    },
    {
        "query": "Teacher transfer rules 2023",
        "expected_text": ["transfer", "teacher", "counseling", "points"],
        "type": "policy_lookup"
    }
]

def run_eval():
    # Load environment if accessible
    try:
        load_dotenv()
    except PermissionError as exc:
        print(f"⚠️ Could not load .env file: {exc}. Continuing with existing environment.")
    
    logger.info("🚀 Initializing V3 Engine for Eval...")
    
    # Validate config (allow missing API keys in test env)
    validate_config(allow_missing_llm=True)
    
    qdrant = get_qdrant_client()
    embedder = get_embedder()
    
    engine = RetrievalEngine(
        qdrant_client=qdrant,
        embedder=embedder,
        use_llm_rewrites=False, # Disable for speed in eval
        use_llm_reranking=False, # Disable for speed
        use_cross_encoder=True, # Enable our new reranker
        enable_cache=True
    )
    
    results_log = []
    
    logger.info(f"🧪 Running {len(GOLDEN_QUERIES)} golden queries...")
    
    for item in GOLDEN_QUERIES:
        query = item["query"]
        logger.info(f"\nQuery: {query}")
        
        start = time.time()
        output = engine.retrieve(query, top_k=5)
        elapsed = time.time() - start
        
        # Check recall
        found_keywords = 0
        top_result_text = output.results[0].content if output.results else ""
        all_text = " ".join([r.content for r in output.results])
        
        matches = []
        for kw in item["expected_text"]:
            if kw.lower() in all_text.lower():
                found_keywords += 1
                matches.append(kw)
                
        recall_score = found_keywords / len(item["expected_text"])
        
        logger.info(f"  Time: {elapsed:.2f}s")
        logger.info(f"  Results: {len(output.results)}")
        logger.info(f"  Recall Score: {recall_score:.2f} ({matches})")
        if output.results:
            logger.info(f"  Top Result: {output.results[0].content[:100]}...")
            logger.info(f"  Top Score: {output.results[0].score:.4f}")
            
        results_log.append({
            "query": query,
            "recall": recall_score,
            "time": elapsed
        })
        
    # Summary
    avg_recall = sum(r["recall"] for r in results_log) / len(results_log)
    avg_time = sum(r["time"] for r in results_log) / len(results_log)
    
    logger.info("\n" + "="*50)
    logger.info(f"EVAL SUMMARY")
    logger.info(f"Avg Recall: {avg_recall:.2f}")
    logger.info(f"Avg Time: {avg_time:.2f}s")
    logger.info("="*50)

if __name__ == "__main__":
    run_eval()
