#!/usr/bin/env python3
"""
Complete Pipeline Test Suite
===========================
Tests the entire retrieval and answer generation pipeline including:

1. Infrastructure: Qdrant connectivity, embedding consistency
2. Query Processing: All 3 modes (QA, Deep Think, Brainstorm) 
3. Answer Generation: Persona, citations, structured responses
4. Output Formatting: Citations, metadata, structured output
5. End-to-End: Real queries against uploaded data

Based on actual uploaded data: 689 chunks across 5 collections.
"""

import os
import json
import time
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass
from datetime import datetime
from statistics import fmean
from dotenv import load_dotenv

# Try to import numpy, use fallback if not available
try:
    import numpy as np
except ImportError:
    # Simple numpy fallback for basic operations
    class SimpleNP:
        @staticmethod
        def mean(values):
            return sum(values) / len(values) if values else 0
        @staticmethod  
        def linalg():
            class Linalg:
                @staticmethod
                def norm(vector):
                    return sum(x*x for x in vector) ** 0.5
            return Linalg()
    np = SimpleNP()

# Load environment if accessible
try:
    load_dotenv()
except PermissionError as exc:
    print(f"⚠️ Could not load .env file: {exc}. Continuing with existing environment.")

# Add current directory to Python path to enable retrieval package import
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Import retrieval system as proper package
import retrieval
from retrieval import RetrievalRouter, get_answer_generator
from retrieval.config.settings import validate_config
from retrieval.config.mode_config import QueryMode  
from retrieval.config.vertical_map import get_all_collections
from retrieval.retrieval_core.qdrant_client import get_qdrant_client
from retrieval.embeddings.embedder import get_embedder
from retrieval.output_formatting.formatter import get_formatter
from retrieval.output_formatting.citations import get_citation_manager

@dataclass
class TestResult:
    """Test result structure"""
    test_name: str
    passed: bool
    message: str
    details: Dict = None
    duration: float = 0.0

class CompletePipelineTest:
    """Complete pipeline tester with answer generation"""
    
    def __init__(self):
        """Initialize test suite"""
        self.router = None
        self.answer_generator = None
        self.formatter = None
        self.citation_manager = None
        self.qdrant = None
        self.embedder = None
        self.results = []
        
        # Test queries organized by mode and expected behavior
        self.mode_test_queries = {
            QueryMode.QA: {
                "teacher_transfer": {
                    "query": "What are the rules for teacher transfers in AP?",
                    "expected_vertical": "go",
                    "expect_citations": True,
                    "expect_concise": True
                },
                "education_budget": {
                    "query": "What is the education budget allocation for primary schools?", 
                    "expected_vertical": "data",
                    "expect_citations": True,
                    "expect_concise": True
                }
            },
            QueryMode.DEEP_THINK: {
                "teacher_policy": {
                    "query": "Analyze the teacher recruitment and posting policy framework in AP",
                    "expected_verticals": ["legal", "go", "judicial", "data", "schemes"],
                    "expect_structured": True,
                    "expect_comprehensive": True
                },
                "education_governance": {
                    "query": "What is the legal and administrative framework governing primary education?",
                    "expected_verticals": ["legal", "go", "judicial"],
                    "expect_structured": True,
                    "expect_comprehensive": True
                }
            },
            QueryMode.BRAINSTORM: {
                "innovation_ideas": {
                    "query": "How can we improve teacher training and development?",
                    "expected_verticals": ["schemes", "data"],
                    "expect_creative": True,
                    "expect_diverse": True
                },
                "digital_transformation": {
                    "query": "What innovative approaches can modernize education delivery?",
                    "expected_verticals": ["schemes", "data"],
                    "expect_creative": True,
                    "expect_diverse": True
                }
            }
        }
    
    def setup(self) -> bool:
        """Setup test environment"""
        try:
            print("🚀 Setting up complete pipeline test...")
            
            # Validate config (allow missing API keys in test env)
            validate_config(allow_missing_llm=True)
            print("✅ Configuration validated")
            
            # Initialize all components
            self.router = RetrievalRouter()
            self.answer_generator = get_answer_generator()
            self.formatter = get_formatter()
            self.citation_manager = get_citation_manager()
            self.qdrant = get_qdrant_client()
            self.embedder = get_embedder()
            
            print("✅ All components initialized")
            return True
            
        except Exception as e:
            print(f"❌ Setup failed: {e}")
            return False
    
    def test_qdrant_connectivity(self) -> TestResult:
        """Test Qdrant connection and data availability"""
        start = time.time()
        try:
            collections = self.qdrant.get_collections()
            collection_names = [c.name for c in collections.collections]
            expected_collections = get_all_collections()
            
            collection_status = {}
            total_points = 0
            
            for collection in expected_collections:
                if collection in collection_names:
                    try:
                        count = self.qdrant.count(collection)
                        collection_status[collection] = count.count
                        total_points += count.count
                    except Exception as e:
                        collection_status[collection] = f"Error: {e}"
                else:
                    collection_status[collection] = "Missing"
            
            duration = time.time() - start
            
            if total_points >= 600:  # Should have ~689 chunks
                return TestResult(
                    test_name="qdrant_connectivity",
                    passed=True,
                    message=f"✅ Qdrant connected with {total_points} chunks",
                    details={"collections": collection_status, "total_points": total_points},
                    duration=duration
                )
            else:
                return TestResult(
                    test_name="qdrant_connectivity",
                    passed=False,
                    message=f"❌ Insufficient data: {total_points} chunks (expected ~689)",
                    details={"collections": collection_status},
                    duration=duration
                )
                
        except Exception as e:
            return TestResult(
                test_name="qdrant_connectivity",
                passed=False,
                message=f"❌ Qdrant connection failed: {e}",
                duration=time.time() - start
            )
    
    def test_mode_detection_and_routing(self) -> TestResult:
        """Test that queries are properly routed to appropriate modes"""
        start = time.time()
        try:
            test_cases = [
                ("What is Section 12?", QueryMode.QA),
                ("teacher transfer rules", QueryMode.QA),
                ("Analyze the complete education policy framework", QueryMode.DEEP_THINK),
                ("comprehensive review of teacher recruitment", QueryMode.DEEP_THINK),
                ("innovative ideas for education", QueryMode.BRAINSTORM),
                ("creative approaches to teacher training", QueryMode.BRAINSTORM)
            ]
            
            routing_results = {}
            correct_routes = 0
            
            for query_text, expected_mode in test_cases:
                response = self.router.query(query_text, top_k=3)
                
                if response.get("success"):
                    detected_mode = response.get("mode")
                    mode_confidence = response.get("mode_confidence", 0)
                    
                    is_correct = detected_mode == expected_mode.value
                    if is_correct:
                        correct_routes += 1
                    
                    routing_results[query_text] = {
                        "expected": expected_mode.value,
                        "detected": detected_mode,
                        "confidence": mode_confidence,
                        "correct": is_correct,
                        "verticals_searched": response.get("verticals_searched", []),
                        "results_count": len(response.get("results", []))
                    }
                else:
                    routing_results[query_text] = {
                        "error": response.get("error"),
                        "expected": expected_mode.value
                    }
            
            duration = time.time() - start
            success_rate = correct_routes / len(test_cases)
            
            if success_rate >= 0.7:  # 70% accuracy threshold
                return TestResult(
                    test_name="mode_detection",
                    passed=True,
                    message=f"✅ Mode detection: {correct_routes}/{len(test_cases)} correct ({success_rate:.1%})",
                    details=routing_results,
                    duration=duration
                )
            else:
                return TestResult(
                    test_name="mode_detection",
                    passed=False,
                    message=f"❌ Poor mode detection: {correct_routes}/{len(test_cases)} correct ({success_rate:.1%})",
                    details=routing_results,
                    duration=duration
                )
                
        except Exception as e:
            return TestResult(
                test_name="mode_detection",
                passed=False,
                message=f"❌ Mode detection test failed: {e}",
                duration=time.time() - start
            )
    
    def test_qa_mode_complete(self) -> TestResult:
        """Test complete QA mode pipeline with answer generation"""
        start = time.time()
        try:
            query_config = self.mode_test_queries[QueryMode.QA]["teacher_transfer"]
            query = query_config["query"]
            
            # Get retrieval results
            response = self.router.query(query, mode="qa", top_k=5)
            
            if not response.get("success"):
                return TestResult(
                    test_name="qa_mode_complete",
                    passed=False,
                    message=f"❌ QA retrieval failed: {response.get('error')}",
                    duration=time.time() - start
                )
            
            results = response.get("results", [])
            
            # Generate answer
            answer_response = self.answer_generator.generate_qa_answer(query, results)
            
            # Analyze answer quality
            answer_analysis = {
                "has_answer": bool(answer_response.get("answer")),
                "answer_length": len(answer_response.get("answer", "")),
                "has_citations": len(answer_response.get("citations", [])) > 0,
                "model_used": answer_response.get("model"),
                "mode": answer_response.get("mode"),
                "sources_used": answer_response.get("sources_used", 0),
                "is_concise": len(answer_response.get("answer", "")) < 1000  # Should be concise
            }
            
            # Add citations to results
            results_with_citations, bibliography = self.citation_manager.add_citations(results)
            
            # Format complete response
            formatted_response = self.formatter.format_response(
                results=results_with_citations,
                query=query,
                mode="qa",
                mode_confidence=response.get("mode_confidence", 0),
                verticals_searched=response.get("verticals_searched", []),
                vertical_coverage=response.get("vertical_coverage", {}),
                processing_time=response.get("processing_time", 0)
            )
            
            duration = time.time() - start
            
            # Success criteria
            success = (
                answer_analysis["has_answer"] and
                answer_analysis["has_citations"] and
                answer_analysis["is_concise"] and
                answer_analysis["sources_used"] > 0 and
                len(bibliography) > 0
            )
            
            if success:
                return TestResult(
                    test_name="qa_mode_complete",
                    passed=True,
                    message=f"✅ QA mode working: concise answer with {len(bibliography)} citations",
                    details={
                        "analysis": answer_analysis,
                        "bibliography_count": len(bibliography),
                        "answer_preview": answer_response.get("answer", "")[:200] + "...",
                        "formatted_response_keys": list(formatted_response.keys())
                    },
                    duration=duration
                )
            else:
                issues = []
                if not answer_analysis["has_answer"]:
                    issues.append("no answer generated")
                if not answer_analysis["has_citations"]:
                    issues.append("missing citations")
                if not answer_analysis["is_concise"]:
                    issues.append("answer too verbose")
                if answer_analysis["sources_used"] == 0:
                    issues.append("no sources used")
                if len(bibliography) == 0:
                    issues.append("no bibliography")
                
                return TestResult(
                    test_name="qa_mode_complete",
                    passed=False,
                    message=f"❌ QA mode issues: {', '.join(issues)}",
                    details={"analysis": answer_analysis},
                    duration=duration
                )
                
        except Exception as e:
            return TestResult(
                test_name="qa_mode_complete",
                passed=False,
                message=f"❌ QA mode test failed: {e}",
                duration=time.time() - start
            )
    
    def test_deep_think_mode_complete(self) -> TestResult:
        """Test complete Deep Think mode with comprehensive analysis"""
        start = time.time()
        try:
            query_config = self.mode_test_queries[QueryMode.DEEP_THINK]["teacher_policy"]
            query = query_config["query"]
            
            # Get retrieval results
            response = self.router.query(query, mode="deep_think", top_k=20)
            
            if not response.get("success"):
                return TestResult(
                    test_name="deep_think_complete",
                    passed=False,
                    message=f"❌ Deep Think retrieval failed: {response.get('error')}",
                    duration=time.time() - start
                )
            
            results = response.get("results", [])
            
            # Generate comprehensive answer
            answer_response = self.answer_generator.generate_deep_think_answer(query, results)
            
            # Analyze answer structure and quality
            answer_text = answer_response.get("answer", "")
            answer_analysis = {
                "has_answer": bool(answer_text),
                "answer_length": len(answer_text),
                "has_citations": len(answer_response.get("citations", [])) > 0,
                "model_used": answer_response.get("model"),
                "mode": answer_response.get("mode"),
                "sources_used": answer_response.get("sources_used", 0),
                "verticals_covered": answer_response.get("verticals_covered", []),
                "is_comprehensive": len(answer_text) > 1500,  # Should be detailed
                "has_structure": any(marker in answer_text for marker in ["**", "1.", "2.", "##"]),
                "covers_framework": any(term in answer_text.lower() for term in ["legal", "constitutional", "policy", "framework"])
            }
            
            # Check vertical coverage
            expected_verticals = query_config["expected_verticals"]
            verticals_found = set(r.get("vertical") for r in results if r.get("vertical"))
            vertical_coverage = sum(1 for v in expected_verticals if v in verticals_found) / len(expected_verticals)
            
            duration = time.time() - start
            
            # Success criteria for Deep Think
            success = (
                answer_analysis["has_answer"] and
                answer_analysis["has_citations"] and
                answer_analysis["is_comprehensive"] and
                answer_analysis["has_structure"] and
                answer_analysis["covers_framework"] and
                vertical_coverage >= 0.5 and  # At least 50% of expected verticals
                answer_analysis["sources_used"] >= 10  # Should use many sources
            )
            
            if success:
                return TestResult(
                    test_name="deep_think_complete",
                    passed=True,
                    message=f"✅ Deep Think working: comprehensive analysis with {answer_analysis['sources_used']} sources",
                    details={
                        "analysis": answer_analysis,
                        "vertical_coverage": vertical_coverage,
                        "verticals_found": list(verticals_found),
                        "answer_preview": answer_text[:300] + "...",
                    },
                    duration=duration
                )
            else:
                issues = []
                if not answer_analysis["has_answer"]:
                    issues.append("no answer")
                if not answer_analysis["has_citations"]:
                    issues.append("missing citations")
                if not answer_analysis["is_comprehensive"]:
                    issues.append("too brief")
                if not answer_analysis["has_structure"]:
                    issues.append("unstructured")
                if not answer_analysis["covers_framework"]:
                    issues.append("missing framework analysis")
                if vertical_coverage < 0.5:
                    issues.append("poor vertical coverage")
                if answer_analysis["sources_used"] < 10:
                    issues.append("too few sources")
                
                return TestResult(
                    test_name="deep_think_complete",
                    passed=False,
                    message=f"❌ Deep Think issues: {', '.join(issues)}",
                    details={"analysis": answer_analysis, "vertical_coverage": vertical_coverage},
                    duration=duration
                )
                
        except Exception as e:
            return TestResult(
                test_name="deep_think_complete",
                passed=False,
                message=f"❌ Deep Think test failed: {e}",
                duration=time.time() - start
            )
    
    def test_brainstorm_mode_complete(self) -> TestResult:
        """Test complete Brainstorm mode with creative synthesis"""
        start = time.time()
        try:
            query_config = self.mode_test_queries[QueryMode.BRAINSTORM]["innovation_ideas"]
            query = query_config["query"]
            
            # Get retrieval results
            response = self.router.query(query, mode="brainstorm", top_k=15)
            
            if not response.get("success"):
                return TestResult(
                    test_name="brainstorm_complete",
                    passed=False,
                    message=f"❌ Brainstorm retrieval failed: {response.get('error')}",
                    duration=time.time() - start
                )
            
            results = response.get("results", [])
            
            # Generate creative answer
            answer_response = self.answer_generator.generate_brainstorm_answer(query, results)
            
            # Analyze creativity and structure
            answer_text = answer_response.get("answer", "")
            answer_analysis = {
                "has_answer": bool(answer_text),
                "answer_length": len(answer_text),
                "has_citations": len(answer_response.get("citations", [])) > 0,
                "model_used": answer_response.get("model"),
                "mode": answer_response.get("mode"),
                "sources_used": answer_response.get("sources_used", 0),
                "is_creative": any(term in answer_text.lower() for term in ["innovative", "creative", "novel", "innovative", "global", "best practice"]),
                "has_ideas": any(marker in answer_text for marker in ["1.", "2.", "3.", "**"]),
                "mentions_global": any(term in answer_text.lower() for term in ["international", "global", "finland", "singapore", "best practice"]),
                "actionable": any(term in answer_text.lower() for term in ["implement", "pilot", "action", "recommend", "strategy"])
            }
            
            # Check for focus on schemes and data (Brainstorm mode preference)
            expected_verticals = query_config["expected_verticals"]
            verticals_found = set(r.get("vertical") for r in results if r.get("vertical"))
            has_expected_focus = any(v in verticals_found for v in expected_verticals)
            
            duration = time.time() - start
            
            # Success criteria for Brainstorm
            success = (
                answer_analysis["has_answer"] and
                answer_analysis["is_creative"] and
                answer_analysis["has_ideas"] and
                answer_analysis["actionable"] and
                has_expected_focus and
                answer_analysis["sources_used"] > 0
            )
            
            if success:
                return TestResult(
                    test_name="brainstorm_complete",
                    passed=True,
                    message=f"✅ Brainstorm working: creative ideas with {answer_analysis['sources_used']} sources",
                    details={
                        "analysis": answer_analysis,
                        "verticals_found": list(verticals_found),
                        "answer_preview": answer_text[:300] + "...",
                    },
                    duration=duration
                )
            else:
                issues = []
                if not answer_analysis["has_answer"]:
                    issues.append("no answer")
                if not answer_analysis["is_creative"]:
                    issues.append("not creative")
                if not answer_analysis["has_ideas"]:
                    issues.append("no structured ideas")
                if not answer_analysis["actionable"]:
                    issues.append("not actionable")
                if not has_expected_focus:
                    issues.append("wrong vertical focus")
                
                return TestResult(
                    test_name="brainstorm_complete",
                    passed=False,
                    message=f"❌ Brainstorm issues: {', '.join(issues)}",
                    details={"analysis": answer_analysis},
                    duration=duration
                )
                
        except Exception as e:
            return TestResult(
                test_name="brainstorm_complete",
                passed=False,
                message=f"❌ Brainstorm test failed: {e}",
                duration=time.time() - start
            )
    
    def test_persona_and_formatting(self) -> TestResult:
        """Test that persona comes through in answers and formatting is proper"""
        start = time.time()
        try:
            # Test each mode's persona
            persona_tests = [
                ("qa", "What is Section 12?", ["factual", "direct", "precise"]),
                ("deep_think", "Analyze education policy", ["comprehensive", "analysis", "framework", "policy"]),
                ("brainstorm", "Creative education ideas", ["innovative", "creative", "ideas", "global"])
            ]
            
            persona_results = {}
            
            for mode, query, expected_markers in persona_tests:
                response = self.router.query(query, mode=mode, top_k=5)
                
                if response.get("success"):
                    results = response.get("results", [])
                    
                    # Generate answer based on mode
                    if mode == "qa":
                        answer_response = self.answer_generator.generate_qa_answer(query, results)
                    elif mode == "deep_think":
                        answer_response = self.answer_generator.generate_deep_think_answer(query, results)
                    else:  # brainstorm
                        answer_response = self.answer_generator.generate_brainstorm_answer(query, results)
                    
                    answer_text = answer_response.get("answer", "").lower()
                    
                    # Check for persona markers
                    persona_score = sum(1 for marker in expected_markers if marker in answer_text) / len(expected_markers)
                    
                    # Check formatting
                    formatted_response = self.formatter.format_response(
                        results=results,
                        query=query,
                        mode=mode,
                        mode_confidence=0.9,
                        verticals_searched=["go", "legal"],
                        vertical_coverage={"go": 2, "legal": 3},
                        processing_time=1.0
                    )
                    
                    formatting_check = {
                        "has_success": formatted_response.get("success") is True,
                        "has_timestamp": "timestamp" in formatted_response,
                        "has_query_section": "query" in formatted_response,
                        "has_search_section": "search" in formatted_response,
                        "has_results": "results" in formatted_response,
                        "has_performance": "performance" in formatted_response
                    }
                    
                    persona_results[mode] = {
                        "persona_score": persona_score,
                        "expected_markers": expected_markers,
                        "found_markers": [m for m in expected_markers if m in answer_text],
                        "formatting_score": sum(formatting_check.values()) / len(formatting_check),
                        "formatting_details": formatting_check,
                        "answer_length": len(answer_response.get("answer", "")),
                        "model_used": answer_response.get("model")
                    }
                else:
                    persona_results[mode] = {"error": response.get("error")}
            
            # Calculate overall success
            successful_modes = [m for m, r in persona_results.items() 
                             if "error" not in r and r.get("persona_score", 0) >= 0.5 and r.get("formatting_score", 0) >= 0.8]
            
            duration = time.time() - start
            
            if len(successful_modes) >= 2:  # At least 2 out of 3 modes working well
                return TestResult(
                    test_name="persona_formatting",
                    passed=True,
                    message=f"✅ Persona and formatting working: {len(successful_modes)}/3 modes good",
                    details=persona_results,
                    duration=duration
                )
            else:
                return TestResult(
                    test_name="persona_formatting",
                    passed=False,
                    message=f"❌ Persona/formatting issues: only {len(successful_modes)}/3 modes working",
                    details=persona_results,
                    duration=duration
                )
                
        except Exception as e:
            return TestResult(
                test_name="persona_formatting",
                passed=False,
                message=f"❌ Persona/formatting test failed: {e}",
                duration=time.time() - start
            )
    
    def test_citations_and_bibliography(self) -> TestResult:
        """Test citation extraction and bibliography generation"""
        start = time.time()
        try:
            # Get some results for citation testing
            response = self.router.query("teacher transfer rules", top_k=5)
            
            if not response.get("success"):
                return TestResult(
                    test_name="citations_bibliography",
                    passed=False,
                    message=f"❌ Could not get results for citation test: {response.get('error')}",
                    duration=time.time() - start
                )
            
            results = response.get("results", [])
            
            if not results:
                return TestResult(
                    test_name="citations_bibliography",
                    passed=False,
                    message="❌ No results to test citations",
                    duration=time.time() - start
                )
            
            # Test citation addition
            results_with_citations, bibliography = self.citation_manager.add_citations(results)
            
            # Generate answer with citations
            answer_response = self.answer_generator.generate_qa_answer("teacher transfer rules", results)
            
            # Build bibliography section
            bibliography_text = self.citation_manager.build_bibliography_section(bibliography)
            
            # Analyze citation quality
            citation_analysis = {
                "results_have_citations": all("citation_number" in r for r in results_with_citations),
                "bibliography_count": len(bibliography),
                "bibliography_has_content": len(bibliography_text) > 50,
                "answer_has_citations": len(answer_response.get("citations", [])) > 0,
                "citations_in_answer": answer_response.get("citations", []),
                "bibliography_entries_valid": all(
                    b.get("number") and b.get("text") and b.get("source") 
                    for b in bibliography
                )
            }
            
            duration = time.time() - start
            
            # Success criteria
            success = (
                citation_analysis["results_have_citations"] and
                citation_analysis["bibliography_count"] > 0 and
                citation_analysis["bibliography_has_content"] and
                citation_analysis["bibliography_entries_valid"] and
                citation_analysis["answer_has_citations"]
            )
            
            if success:
                return TestResult(
                    test_name="citations_bibliography",
                    passed=True,
                    message=f"✅ Citations working: {len(bibliography)} entries with proper formatting",
                    details={
                        "analysis": citation_analysis,
                        "sample_bibliography_entry": bibliography[0] if bibliography else None,
                        "bibliography_preview": bibliography_text[:200] + "..." if bibliography_text else ""
                    },
                    duration=duration
                )
            else:
                issues = []
                if not citation_analysis["results_have_citations"]:
                    issues.append("results missing citations")
                if citation_analysis["bibliography_count"] == 0:
                    issues.append("no bibliography")
                if not citation_analysis["bibliography_has_content"]:
                    issues.append("empty bibliography")
                if not citation_analysis["bibliography_entries_valid"]:
                    issues.append("invalid bibliography entries")
                if not citation_analysis["answer_has_citations"]:
                    issues.append("answer missing citations")
                
                return TestResult(
                    test_name="citations_bibliography",
                    passed=False,
                    message=f"❌ Citation issues: {', '.join(issues)}",
                    details=citation_analysis,
                    duration=duration
                )
                
        except Exception as e:
            return TestResult(
                test_name="citations_bibliography",
                passed=False,
                message=f"❌ Citations test failed: {e}",
                duration=time.time() - start
            )
    
    def run_comprehensive_tests(self) -> Dict:
        """Run all tests and return comprehensive report"""
        print("🧪 Starting COMPLETE pipeline tests (retrieval + answer generation)...")
        start_time = time.time()
        
        # Setup
        if not self.setup():
            return {"error": "Setup failed"}
        
        print("\n" + "="*70)
        print("COMPLETE PIPELINE TEST SUITE")
        print("="*70)
        
        # Infrastructure tests
        print("\n🔧 Testing Infrastructure...")
        self.results.append(self.test_qdrant_connectivity())
        
        # Core pipeline tests
        print("\n🎯 Testing Mode Detection & Routing...")
        self.results.append(self.test_mode_detection_and_routing())
        
        # Mode-specific complete tests
        print("\n📋 Testing QA Mode (Complete Pipeline)...")
        self.results.append(self.test_qa_mode_complete())
        
        print("\n🧠 Testing Deep Think Mode (Complete Pipeline)...")
        self.results.append(self.test_deep_think_mode_complete())
        
        print("\n💡 Testing Brainstorm Mode (Complete Pipeline)...")
        self.results.append(self.test_brainstorm_mode_complete())
        
        # Output quality tests
        print("\n🎭 Testing Persona & Formatting...")
        self.results.append(self.test_persona_and_formatting())
        
        print("\n📚 Testing Citations & Bibliography...")
        self.results.append(self.test_citations_and_bibliography())
        
        # Generate comprehensive report
        return self._generate_final_report(start_time)
    
    def _generate_final_report(self, start_time: float) -> Dict:
        """Generate comprehensive final report"""
        total_time = time.time() - start_time
        
        # Count results
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        total = len(self.results)
        
        # Categorize results
        infrastructure = [r for r in self.results if "connectivity" in r.test_name]
        mode_tests = [r for r in self.results if "mode" in r.test_name]
        pipeline_tests = [r for r in self.results if "complete" in r.test_name]
        output_tests = [r for r in self.results if r.test_name in ["persona_formatting", "citations_bibliography"]]
        
        # Print detailed summary
        print("\n" + "="*70)
        print("FINAL TEST RESULTS")
        print("="*70)
        
        print(f"\n📊 Overall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
        
        for category, tests in [
            ("🔧 Infrastructure", infrastructure),
            ("🎯 Mode & Routing", mode_tests),
            ("🚀 Complete Pipelines", pipeline_tests),
            ("🎨 Output Quality", output_tests)
        ]:
            if tests:
                cat_passed = sum(1 for t in tests if t.passed)
                cat_total = len(tests)
                print(f"{category}: {cat_passed}/{cat_total} passed")
                
                for test in tests:
                    status = "✅" if test.passed else "❌"
                    print(f"  {status} {test.test_name}: {test.message}")
        
        print(f"\n⏱️ Total execution time: {total_time:.2f}s")
        
        # Assessment
        print("\n" + "="*70)
        print("SYSTEM READINESS ASSESSMENT")
        print("="*70)
        
        success_rate = passed / total if total > 0 else 0
        
        if success_rate >= 0.85:
            print("🎉 EXCELLENT: System is production-ready!")
            print("   ✅ All major components working correctly")
            print("   ✅ Proper persona and answer generation")
            print("   ✅ Citations and formatting working")
            assessment = "production_ready"
        elif success_rate >= 0.7:
            print("⚠️ GOOD: System mostly working with minor issues")
            print("   ✅ Core functionality operational") 
            print("   ⚠️ Some components need refinement")
            assessment = "mostly_ready"
        else:
            print("❌ NEEDS WORK: Significant issues found")
            print("   ❌ Multiple components failing")
            print("   ❌ Not ready for production use")
            assessment = "needs_work"
        
        print(f"\n📈 Success Rate: {success_rate*100:.1f}%")
        
        # Detailed report
        report = {
            "summary": {
                "assessment": assessment,
                "total_tests": total,
                "passed": passed,
                "failed": failed,
                "success_rate": success_rate,
                "execution_time": total_time,
                "timestamp": datetime.now().isoformat()
            },
            "categories": {
                "infrastructure": self._summarize_category(infrastructure),
                "mode_routing": self._summarize_category(mode_tests),
                "complete_pipelines": self._summarize_category(pipeline_tests),
                "output_quality": self._summarize_category(output_tests)
            },
            "detailed_results": [
                {
                    "test_name": r.test_name,
                    "passed": r.passed,
                    "message": r.message,
                    "duration": r.duration,
                    "details": r.details
                }
                for r in self.results
            ]
        }
        
        # Save report
        self._save_report(report)
        
        return report
    
    def _summarize_category(self, tests: List[TestResult]) -> Dict:
        """Summarize test category"""
        if not tests:
            return {"passed": 0, "total": 0, "success_rate": 0}
        
        passed = sum(1 for t in tests if t.passed)
        total = len(tests)
        
        return {
            "passed": passed,
            "total": total,
            "success_rate": passed / total,
            "avg_duration": fmean([t.duration for t in tests]) if tests else 0.0
        }
    
    def _save_report(self, report: Dict):
        """Save comprehensive test report"""
        report_file = f"complete_pipeline_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"\n📝 Detailed report saved: {report_file}")
        except Exception as e:
            print(f"\n⚠️ Could not save report: {e}")

def main():
    """Run comprehensive pipeline tests"""
    tester = CompletePipelineTest()
    report = tester.run_comprehensive_tests()
    
    return report

if __name__ == "__main__":
    main()