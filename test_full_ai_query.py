#!/usr/bin/env python3
"""
Test Full AI Query Pipeline
==========================
Test the complete pipeline for "I want to change school syllabus integrating AI" 
to see if we get a better answer now.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
try:
    load_dotenv()
except PermissionError as exc:
    print(f"⚠️ Could not load .env file: {exc}. Continuing with existing environment.")

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

def test_full_ai_query():
    """Test the complete pipeline for AI curriculum integration"""
    print("🎯 Testing FULL Pipeline: AI Curriculum Integration")
    print("=" * 65)
    
    query = "I want to change school syllabus integrating AI"
    print(f"Query: '{query}'")
    print("-" * 65)
    
    try:
        from retrieval.router import RetrievalRouter
        from retrieval import get_answer_generator
        from retrieval.output_formatting.formatter import get_formatter
        from retrieval.output_formatting.citations import get_citation_manager
        
        # Initialize components
        print("🚀 Initializing components...")
        router = RetrievalRouter()
        answer_generator = get_answer_generator()
        formatter = get_formatter()
        citation_manager = get_citation_manager()
        
        # Step 1: Get enhanced retrieval results
        print("\n📋 STEP 1: Enhanced Retrieval")
        response = router.query(query, mode="deep_think", top_k=20)
        
        if not response.get("success"):
            print(f"❌ Retrieval failed: {response.get('error')}")
            return
        
        results = response.get("results", [])
        print(f"   ✅ Retrieved {len(results)} results")
        print(f"   Collections: {response.get('verticals_searched', [])}")
        
        # Show top results with sources
        print("\n   📄 Top Results:")
        for i, result in enumerate(results[:5], 1):
            source = result.get("source", "Unknown")
            vertical = result.get("vertical", "Unknown")
            score = result.get("score", 0)
            text_preview = result.get("text", "")[:120] + "..."
            
            print(f"   {i}. [{vertical}] {source} (Score: {score:.3f})")
            print(f"      {text_preview}")
            print()
        
        # Step 2: Generate enhanced answer
        print("📋 STEP 2: Answer Generation")
        answer_response = answer_generator.generate_deep_think_answer(query, results)
        
        answer = answer_response.get("answer", "")
        citations = answer_response.get("citations", [])
        
        print(f"   ✅ Generated answer: {len(answer)} characters")
        print(f"   ✅ Citations: {len(citations)}")
        
        # Step 3: Add citations and format
        print("\n📋 STEP 3: Citation & Formatting")
        results_with_citations, bibliography = citation_manager.add_citations(results)
        
        formatted_response = formatter.format_response(
            results=results_with_citations,
            query=query,
            mode="deep_think",
            mode_confidence=response.get("mode_confidence", 0),
            verticals_searched=response.get("verticals_searched", []),
            vertical_coverage=response.get("vertical_coverage", {}),
            processing_time=response.get("processing_time", 0)
        )
        
        print(f"   ✅ Bibliography entries: {len(bibliography)}")
        print(f"   ✅ Formatted response keys: {list(formatted_response.keys())}")
        
        # Step 4: Show the final answer
        print("\n" + "=" * 65)
        print("FINAL ENHANCED ANSWER")
        print("=" * 65)
        
        print("\n📝 ANSWER:")
        print(answer[:1000] + "..." if len(answer) > 1000 else answer)
        
        print(f"\n📚 CITATIONS ({len(citations)}):")
        for i, citation in enumerate(citations[:5], 1):
            print(f"   {i}. {citation}")
        
        print(f"\n📖 BIBLIOGRAPHY ({len(bibliography)}):")
        for i, bib_entry in enumerate(bibliography[:5], 1):
            number = bib_entry.get("number", i)
            text = bib_entry.get("text", "")[:100] + "..."
            source = bib_entry.get("source", "Unknown")
            
            print(f"   [{number}] {source}")
            print(f"       {text}")
            print()
        
        # Analysis
        print("\n" + "=" * 65)
        print("ANALYSIS")
        print("=" * 65)
        
        # Check for key education initiatives mentioned
        answer_lower = answer.lower()
        initiatives_found = []
        
        key_initiatives = [
            ("Atal Tinkering Lab", ["atal tinkering", "atl"]),
            ("NEP 2020", ["nep 2020", "national education policy 2020"]),
            ("Samagra Shiksha", ["samagra shiksha"]),
            ("Mana Badi Nadu-Nedu", ["mana badi", "nadu nedu"]),
            ("DIKSHA Platform", ["diksha"]),
            ("Technology Integration", ["technology integration", "digital education", "ict"])
        ]
        
        for initiative_name, search_terms in key_initiatives:
            if any(term in answer_lower for term in search_terms):
                initiatives_found.append(initiative_name)
        
        print(f"✅ Education Initiatives Mentioned: {len(initiatives_found)}/6")
        for initiative in initiatives_found:
            print(f"   • {initiative}")
        
        if not initiatives_found:
            print("❌ No specific education initiatives mentioned")
        
        # Check answer quality
        quality_indicators = {
            "Comprehensive": len(answer) > 1500,
            "Well-cited": len(citations) > 5,
            "Multiple sources": len(results) > 15,
            "Multiple collections": len(response.get("verticals_searched", [])) > 2,
            "High relevance": any(r.get("score", 0) > 0.7 for r in results[:5])
        }
        
        print(f"\n📊 Quality Indicators:")
        for indicator, passed in quality_indicators.items():
            status = "✅" if passed else "❌"
            print(f"   {status} {indicator}")
        
        score = sum(quality_indicators.values()) / len(quality_indicators)
        print(f"\n🎯 Overall Quality Score: {score:.1%}")
        
        if score >= 0.8:
            print("🎉 EXCELLENT: Enhanced pipeline working well!")
        elif score >= 0.6:
            print("✅ GOOD: Significant improvement achieved")
        else:
            print("⚠️ NEEDS MORE WORK: Further enhancements needed")
            
    except Exception as e:
        print(f"❌ Pipeline test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_full_ai_query()