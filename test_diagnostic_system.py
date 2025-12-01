#!/usr/bin/env python3
"""
Comprehensive Diagnostic Test
Tests the full system and identifies what's lacking
"""
import sys
import os
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

sys.path.insert(0, 'retrieval_v3')
sys.path.insert(0, 'retrieval')

from dotenv import load_dotenv
load_dotenv()

print("\n" + "="*80)
print("🔍 COMPREHENSIVE DIAGNOSTIC TEST")
print("="*80)

# Test queries representing different use cases
TEST_QUERIES = [
    {
        'query': 'recent GOs on teacher transfers in School Education Department',
        'expected_topics': ['transfers', 'teachers', 'school education'],
        'use_case': 'Recent Policy Updates'
    },
    {
        'query': 'implementation guide for NEP 2020 in AP government schools',
        'expected_topics': ['NEP', 'implementation', 'government schools'],
        'use_case': 'Implementation Guidance'
    },
    {
        'query': 'compliance check for midday meal scheme',
        'expected_topics': ['midday meal', 'compliance', 'requirements'],
        'use_case': 'Compliance Check'
    }
]

def test_layer_1_retrieval():
    """Test Layer 1: Retrieval Quality"""
    print("\n" + "="*80)
    print("LAYER 1: RETRIEVAL QUALITY TEST")
    print("="*80)
    
    try:
        from retrieval.retrieval_core.qdrant_client import get_qdrant_client
        from retrieval.embeddings.embedder import get_embedder
        from retrieval_v3.pipeline.retrieval_engine import RetrievalEngine
        from retrieval_v3.diagnostics.retrieval_debugger import RetrievalDebugger
        
        # Initialize engine
        engine = RetrievalEngine(
            qdrant_client=get_qdrant_client(),
            embedder=get_embedder(),
            use_llm_rewrites=False,
            enable_cache=True
        )
        
        debugger = RetrievalDebugger()
        
        issues_found = []
        
        for test in TEST_QUERIES:
            print(f"\n📋 Testing: {test['use_case']}")
            print(f"   Query: {test['query']}")
            
            # Retrieve
            start = time.time()
            output = engine.retrieve(test['query'])
            latency = time.time() - start
            
            # Debug retrieval
            results_for_debug = [
                {
                    'content': r.content,
                    'doc_id': r.doc_id,
                    'score': r.score,
                    'go_number': r.metadata.get('go_number'),
                    'date': r.metadata.get('date'),
                    'department': r.metadata.get('department')
                }
                for r in output.results
            ]
            
            debug_report = debugger.debug_retrieval(
                query=test['query'],
                results=results_for_debug,
                expected_topics=test['expected_topics']
            )
            
            print(f"   ✓ Retrieved: {len(output.results)} documents")
            print(f"   ✓ Latency: {latency:.2f}s")
            print(f"   ✓ Quality Grade: {debug_report.quality_grade}")
            print(f"   ✓ Avg Relevance: {sum(debug_report.relevance_scores)/len(debug_report.relevance_scores) if debug_report.relevance_scores else 0:.2f}")
            print(f"   ✓ Coverage: {debug_report.coverage_score:.2f}")
            
            if debug_report.issues:
                print(f"   ⚠️  Issues: {len(debug_report.issues)}")
                for issue in debug_report.issues:
                    print(f"      - {issue}")
                    issues_found.append(f"{test['use_case']}: {issue}")
            
            if debug_report.recommendations:
                print(f"   💡 Recommendations:")
                for rec in debug_report.recommendations:
                    print(f"      - {rec}")
        
        print(f"\n📊 LAYER 1 SUMMARY:")
        print(f"   Total Issues: {len(issues_found)}")
        if issues_found:
            print(f"   ❌ RETRIEVAL NEEDS IMPROVEMENT")
            return False, issues_found
        else:
            print(f"   ✅ RETRIEVAL QUALITY GOOD")
            return True, []
            
    except Exception as e:
        print(f"   ❌ Layer 1 Test Failed: {e}")
        import traceback
        traceback.print_exc()
        return False, [f"Test execution error: {e}"]

def test_layer_2_context_relevance():
    """Test Layer 2: Context Relevance"""
    print("\n" + "="*80)
    print("LAYER 2: CONTEXT RELEVANCE TEST")
    print("="*80)
    
    try:
        from retrieval.retrieval_core.qdrant_client import get_qdrant_client
        from retrieval.embeddings.embedder import get_embedder
        from retrieval_v3.pipeline.retrieval_engine import RetrievalEngine
        
        engine = RetrievalEngine(
            qdrant_client=get_qdrant_client(),
            embedder=get_embedder()
        )
        
        issues_found = []
        
        for test in TEST_QUERIES:
            print(f"\n📋 Testing: {test['use_case']}")
            
            output = engine.retrieve(test['query'])
            
            # Check if top results are relevant
            top_5 = output.results[:5]
            relevant_count = 0
            
            for i, result in enumerate(top_5):
                content_lower = result.content.lower()
                query_terms = test['query'].lower().split()
                
                # Check if at least 30% of query terms appear
                matches = sum(1 for term in query_terms if term in content_lower)
                relevance = matches / len(query_terms)
                
                if relevance >= 0.3:
                    relevant_count += 1
                
                print(f"   Result {i+1}: Relevance {relevance:.2f}")
            
            relevance_rate = relevant_count / len(top_5) if top_5 else 0
            print(f"   ✓ Relevance Rate: {relevance_rate:.0%}")
            
            if relevance_rate < 0.6:
                issue = f"{test['use_case']}: Low relevance rate ({relevance_rate:.0%})"
                issues_found.append(issue)
                print(f"   ⚠️  {issue}")
        
        print(f"\n📊 LAYER 2 SUMMARY:")
        print(f"   Total Issues: {len(issues_found)}")
        if issues_found:
            print(f"   ❌ CONTEXT RELEVANCE NEEDS IMPROVEMENT")
            return False, issues_found
        else:
            print(f"   ✅ CONTEXT RELEVANCE GOOD")
            return True, []
            
    except Exception as e:
        print(f"   ❌ Layer 2 Test Failed: {e}")
        return False, [f"Test execution error: {e}"]

def test_layer_3_prompt_structure():
    """Test Layer 3: Prompt Structure"""
    print("\n" + "="*80)
    print("LAYER 3: PROMPT STRUCTURE TEST")
    print("="*80)
    
    try:
        from retrieval_v3.answer_generation.policy_templates import get_policy_template
        from retrieval_v3.answer_generation.diagnostic_prompts import get_diagnostic_prompt
        
        issues_found = []
        
        # Test if templates are properly structured
        test_query = "teacher recruitment policy"
        test_docs = "Sample document content"
        
        modes = ['brief', 'implementation', 'compliance', 'decision']
        
        for mode in modes:
            print(f"\n📋 Testing: {mode} template")
            
            try:
                template = get_policy_template(mode, test_query, test_docs)
                
                # Check if template has required sections
                required_sections = {
                    'brief': ['BACKGROUND', 'CURRENT POLICY', 'RECOMMENDATIONS'],
                    'implementation': ['OBJECTIVE', 'STEP-BY-STEP', 'ROLES'],
                    'compliance': ['REQUIREMENTS', 'COMPLIANCE SUMMARY', 'GAPS'],
                    'decision': ['DECISION REQUIRED', 'OPTIONS', 'RECOMMENDATION']
                }
                
                missing = []
                for section in required_sections.get(mode, []):
                    if section not in template:
                        missing.append(section)
                
                if missing:
                    issue = f"{mode} template missing sections: {missing}"
                    issues_found.append(issue)
                    print(f"   ⚠️  {issue}")
                else:
                    print(f"   ✅ All required sections present")
                    
            except Exception as e:
                issue = f"{mode} template error: {e}"
                issues_found.append(issue)
                print(f"   ❌ {issue}")
        
        # Test diagnostic prompts
        print(f"\n📋 Testing: Diagnostic prompts")
        diagnostic_modes = ['comprehensive', 'retrieval', 'structure']
        
        for mode in diagnostic_modes:
            try:
                prompt = get_diagnostic_prompt(test_query, test_docs, mode=mode)
                if len(prompt) < 100:
                    issue = f"{mode} diagnostic prompt too short"
                    issues_found.append(issue)
                    print(f"   ⚠️  {issue}")
                else:
                    print(f"   ✅ {mode} prompt OK")
            except Exception as e:
                issue = f"{mode} diagnostic error: {e}"
                issues_found.append(issue)
                print(f"   ❌ {issue}")
        
        print(f"\n📊 LAYER 3 SUMMARY:")
        print(f"   Total Issues: {len(issues_found)}")
        if issues_found:
            print(f"   ❌ PROMPT STRUCTURE NEEDS IMPROVEMENT")
            return False, issues_found
        else:
            print(f"   ✅ PROMPT STRUCTURE GOOD")
            return True, []
            
    except Exception as e:
        print(f"   ❌ Layer 3 Test Failed: {e}")
        import traceback
        traceback.print_exc()
        return False, [f"Test execution error: {e}"]

def test_layer_4_output_quality():
    """Test Layer 4: Output Quality"""
    print("\n" + "="*80)
    print("LAYER 4: OUTPUT QUALITY TEST")
    print("="*80)
    
    try:
        from retrieval.retrieval_core.qdrant_client import get_qdrant_client
        from retrieval.embeddings.embedder import get_embedder
        from retrieval_v3.pipeline.retrieval_engine import RetrievalEngine
        
        engine = RetrievalEngine(
            qdrant_client=get_qdrant_client(),
            embedder=get_embedder()
        )
        
        issues_found = []
        
        # Test one query end-to-end
        test = TEST_QUERIES[0]
        print(f"\n📋 Testing: {test['query']}")
        
        try:
            output = engine.retrieve_and_answer(test['query'], mode='qa')
            answer = output.answer.content
            
            print(f"   ✓ Answer generated ({len(answer)} chars)")
            
            # Check answer quality
            quality_checks = {
                'Has citations': 'G.O.' in answer or 'GO' in answer,
                'Has dates': any(year in answer for year in ['2023', '2024', '2025']),
                'Has structure': len(answer.split('\n')) > 3,
                'Sufficient length': len(answer) > 200
            }
            
            for check, passed in quality_checks.items():
                if passed:
                    print(f"   ✅ {check}")
                else:
                    print(f"   ⚠️  {check}")
                    issues_found.append(f"Answer quality: {check}")
            
        except Exception as e:
            issue = f"Answer generation failed: {e}"
            issues_found.append(issue)
            print(f"   ❌ {issue}")
        
        print(f"\n📊 LAYER 4 SUMMARY:")
        print(f"   Total Issues: {len(issues_found)}")
        if issues_found:
            print(f"   ❌ OUTPUT QUALITY NEEDS IMPROVEMENT")
            return False, issues_found
        else:
            print(f"   ✅ OUTPUT QUALITY GOOD")
            return True, []
            
    except Exception as e:
        print(f"   ❌ Layer 4 Test Failed: {e}")
        import traceback
        traceback.print_exc()
        return False, [f"Test execution error: {e}"]

if __name__ == "__main__":
    print("\n🚀 Starting 4-Layer Diagnostic Test...\n")
    
    all_issues = []
    layer_results = {}
    
    # Test each layer
    layer_1_pass, layer_1_issues = test_layer_1_retrieval()
    layer_results['Layer 1: Retrieval'] = layer_1_pass
    all_issues.extend(layer_1_issues)
    
    layer_2_pass, layer_2_issues = test_layer_2_context_relevance()
    layer_results['Layer 2: Context'] = layer_2_pass
    all_issues.extend(layer_2_issues)
    
    layer_3_pass, layer_3_issues = test_layer_3_prompt_structure()
    layer_results['Layer 3: Prompts'] = layer_3_pass
    all_issues.extend(layer_3_issues)
    
    layer_4_pass, layer_4_issues = test_layer_4_output_quality()
    layer_results['Layer 4: Output'] = layer_4_pass
    all_issues.extend(layer_4_issues)
    
    # Final report
    print("\n" + "="*80)
    print("📊 FINAL DIAGNOSTIC REPORT")
    print("="*80)
    
    for layer, passed in layer_results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{layer}: {status}")
    
    print(f"\n🔍 TOTAL ISSUES FOUND: {len(all_issues)}")
    
    if all_issues:
        print("\n❌ WHAT WE ARE LACKING:\n")
        for i, issue in enumerate(all_issues, 1):
            print(f"{i}. {issue}")
        
        print("\n💡 RECOMMENDED FIXES:\n")
        
        # Categorize issues
        retrieval_issues = [i for i in all_issues if 'retrieval' in i.lower() or 'Layer 1' in i]
        context_issues = [i for i in all_issues if 'relevance' in i.lower() or 'Layer 2' in i]
        prompt_issues = [i for i in all_issues if 'template' in i.lower() or 'prompt' in i.lower() or 'Layer 3' in i]
        output_issues = [i for i in all_issues if 'answer' in i.lower() or 'quality' in i.lower() or 'Layer 4' in i]
        
        if retrieval_issues:
            print("🔧 RETRIEVAL FIXES:")
            print("   - Improve query rewriting")
            print("   - Add more diverse retrieval strategies")
            print("   - Tune BM25 parameters")
            print("   - Add entity-based expansion")
        
        if context_issues:
            print("\n🔧 CONTEXT FIXES:")
            print("   - Improve reranking")
            print("   - Add metadata filters")
            print("   - Enhance cross-encoder scoring")
        
        if prompt_issues:
            print("\n🔧 PROMPT FIXES:")
            print("   - Complete missing template sections")
            print("   - Add more structured prompts")
            print("   - Improve diagnostic prompts")
        
        if output_issues:
            print("\n🔧 OUTPUT FIXES:")
            print("   - Add citation extraction")
            print("   - Improve answer formatting")
            print("   - Add self-verification step")
    else:
        print("\n✅ NO CRITICAL ISSUES FOUND!")
        print("System is performing well across all 4 layers.")
    
    print("\n" + "="*80)
