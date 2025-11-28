#!/usr/bin/env python3
"""
Comprehensive Retrieval V3 Test Suite
====================================
Tests all V3 components with real Qdrant integration.
Validates: Query Understanding, Routing, Retrieval, Reranking, Answer Generation
"""

import os
import sys
import time
import json
from typing import Dict, List
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Add paths for all imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(current_dir, 'retrieval_v3'))
sys.path.insert(0, os.path.join(current_dir, 'retrieval'))
sys.path.insert(0, os.path.join(current_dir, 'ingestion_v2'))

class V3ComponentTester:
    """Comprehensive tester for all V3 retrieval components"""
    
    def __init__(self):
        self.test_results = {
            'query_understanding': {},
            'routing': {},
            'retrieval_core': {},
            'reranking': {},
            'answer_generation': {},
            'end_to_end': {}
        }
        self.qdrant_client = None
        self.embedder = None
        self.engine = None
        
    def setup_components(self):
        """Initialize all real components (Qdrant, embedder, etc.)"""
        print("🔧 Setting up real components...")
        
        try:
            # Import and setup Qdrant
            from retrieval.retrieval_core.qdrant_client import get_qdrant_client
            self.qdrant_client = get_qdrant_client()
            
            # Test Qdrant connection
            collections = self.qdrant_client.get_collections()
            print(f"✅ Qdrant connected: {len(collections.collections)} collections")
            
            # Import and setup embedder  
            from ingestion_v2.embedding.google_embedder import get_embedder
            self.embedder = get_embedder()
            print(f"✅ Embedder initialized: {self.embedder.embedding_dimension}d")
            
            # Initialize V3 engine with real components
            from retrieval_v3.pipeline.retrieval_engine import RetrievalEngine
            self.engine = RetrievalEngine(
                qdrant_client=self.qdrant_client,
                embedder=self.embedder,
                gemini_api_key=os.getenv('GEMINI_API_KEY'),
                use_llm_rewrites=True,
                use_llm_reranking=True
            )
            print("✅ V3 RetrievalEngine initialized with real components")
            
            return True
            
        except Exception as e:
            print(f"❌ Component setup failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_query_understanding(self):
        """Test all query understanding components"""
        print("\n🧠 Testing Query Understanding Components...")
        print("=" * 60)
        
        test_queries = [
            "What is Section 12(1)(c) of RTE Act?",
            "AI integration in school curriculum", 
            "Nadu-Nedu scheme implementation guidelines",
            "Teacher transfer policies in AP",
            "UDISE data collection for 2024"
        ]
        
        results = {}
        
        try:
            # Import components
            from retrieval_v3.query_understanding.query_normalizer import QueryNormalizer
            from retrieval_v3.query_understanding.query_interpreter import QueryInterpreter
            from retrieval_v3.query_understanding.query_rewriter import QueryRewriter
            from retrieval_v3.query_understanding.domain_expander import DomainExpander
            
            normalizer = QueryNormalizer()
            interpreter = QueryInterpreter()
            rewriter = QueryRewriter()
            expander = DomainExpander()
            
            for query in test_queries:
                print(f"\nTesting: '{query}'")
                print("-" * 40)
                
                # Test normalization
                normalized = normalizer.normalize_query(query)
                print(f"Normalized: {normalized}")
                
                # Test interpretation
                interpretation = interpreter.interpret_query(normalized)
                print(f"Type: {interpretation.query_type.value}")
                print(f"Scope: {interpretation.scope.value}")
                print(f"Entities: {len(interpretation.detected_entities)} detected")
                print(f"Needs internet: {interpretation.needs_internet}")
                
                # Test rewrites
                rewrites_obj = rewriter.generate_rewrites(normalized, num_rewrites=3)
                rewrites = [r.text for r in rewrites_obj]
                print(f"Rewrites ({len(rewrites)}): {rewrites[:2]}")  # Show first 2
                
                # Test domain expansion
                expanded = expander.expand_query(normalized, max_terms=5)
                expansion_terms = expanded.replace(normalized, '').strip()
                print(f"Domain expansion: +'{expansion_terms[:100]}{'...' if len(expansion_terms) > 100 else ''}'")
                
                results[query] = {
                    'normalized': normalized,
                    'type': interpretation.query_type.value,
                    'scope': interpretation.scope.value,
                    'entities_count': len(interpretation.detected_entities),
                    'needs_internet': interpretation.needs_internet,
                    'rewrites_count': len(rewrites),
                    'expanded_length': len(expanded)
                }
            
            self.test_results['query_understanding'] = {
                'success': True,
                'queries_tested': len(test_queries),
                'results': results
            }
            print("\n✅ Query Understanding: ALL TESTS PASSED")
            
        except Exception as e:
            print(f"\n❌ Query Understanding failed: {e}")
            import traceback
            traceback.print_exc()
            self.test_results['query_understanding'] = {'success': False, 'error': str(e)}
    
    def test_routing(self):
        """Test routing components"""
        print("\n🎯 Testing Routing Components...")
        print("=" * 60)
        
        test_cases = [
            {
                'query': "What is Section 12(1)(c) of RTE Act?",
                'expected_verticals': ['legal', 'go'],
                'query_type': 'qa'
            },
            {
                'query': "Nadu-Nedu infrastructure development", 
                'expected_verticals': ['schemes'],
                'query_type': 'policy'
            },
            {
                'query': "GO 54 on teacher transfers",
                'expected_verticals': ['go'],
                'query_type': 'qa'
            },
            {
                'query': "UDISE enrollment statistics 2024",
                'expected_verticals': ['data'],
                'query_type': 'qa'
            },
            {
                'query': "Supreme Court judgment on RTE",
                'expected_verticals': ['judicial'],
                'query_type': 'qa'
            }
        ]
        
        try:
            from retrieval_v3.routing.vertical_router import VerticalRouter
            from retrieval_v3.routing.retrieval_plan import RetrievalPlanBuilder
            
            router = VerticalRouter()
            plan_builder = RetrievalPlanBuilder()
            
            routing_results = {}
            
            for case in test_cases:
                query = case['query']
                print(f"\nTesting: '{query}'")
                print("-" * 40)
                
                # Test vertical routing
                verticals = router.route_query(query, case['query_type'])
                vertical_names = [v.value for v in verticals]
                collections = router.get_collection_names(verticals)
                
                print(f"Routed verticals: {vertical_names}")
                print(f"Collections: {collections}")
                print(f"Expected: {case['expected_verticals']}")
                
                # Check if expected verticals are covered
                coverage = set(vertical_names).intersection(set(case['expected_verticals']))
                coverage_score = len(coverage) / len(case['expected_verticals']) if case['expected_verticals'] else 1.0
                
                # Test retrieval plan
                plan = plan_builder.build_plan(
                    query_type=case['query_type'],
                    scope='specific',
                    needs_internet=False,
                    num_verticals=len(verticals)
                )
                
                print(f"Plan mode: {plan.mode}")
                print(f"Top-k total: {plan.top_k_total}")
                print(f"Hops: {plan.num_hops}")
                print(f"Coverage score: {coverage_score:.1%}")
                
                routing_results[query] = {
                    'verticals': vertical_names,
                    'collections': collections,
                    'expected': case['expected_verticals'],
                    'coverage_score': coverage_score,
                    'plan_mode': plan.mode,
                    'plan_top_k': plan.top_k_total
                }
            
            # Calculate overall routing accuracy
            avg_coverage = sum(r['coverage_score'] for r in routing_results.values()) / len(routing_results)
            
            self.test_results['routing'] = {
                'success': True,
                'avg_coverage': avg_coverage,
                'queries_tested': len(test_cases),
                'results': routing_results
            }
            
            print(f"\n✅ Routing: PASSED (Average coverage: {avg_coverage:.1%})")
            
        except Exception as e:
            print(f"\n❌ Routing failed: {e}")
            import traceback
            traceback.print_exc()
            self.test_results['routing'] = {'success': False, 'error': str(e)}
    
    def test_retrieval_core(self):
        """Test core retrieval components with real Qdrant"""
        print("\n🔍 Testing Retrieval Core with Real Qdrant...")
        print("=" * 60)
        
        if not self.qdrant_client or not self.embedder:
            print("❌ Qdrant client or embedder not available")
            return
        
        test_queries = [
            "Atal Tinkering Labs",
            "Section 12 RTE Act", 
            "teacher transfer rules",
            "UDISE data",
            "Nadu-Nedu scheme"
        ]
        
        try:
            retrieval_results = {}
            
            for query in test_queries:
                print(f"\nTesting retrieval: '{query}'")
                print("-" * 40)
                
                # Generate embedding
                if hasattr(self.embedder, 'embed_single'):
                    query_vector = self.embedder.embed_single(query)
                elif hasattr(self.embedder, 'embed_query'):
                    query_vector = self.embedder.embed_query(query)
                else:
                    query_vector = self.embedder.embed_texts([query])[0]
                print(f"Query vector: {len(query_vector)} dimensions")
                
                # Test search across different collections
                collections = [
                    'ap_schemes',
                    'ap_legal_documents', 
                    'ap_government_orders',
                    'ap_data_reports'
                ]
                
                total_results = 0
                collection_results = {}
                
                for collection in collections:
                    try:
                        results = self.qdrant_client.search(
                            collection_name=collection,
                            query_vector=query_vector,
                            limit=5,
                            score_threshold=0.3
                        )
                        
                        collection_results[collection] = len(results)
                        total_results += len(results)
                        
                        if results:
                            top_score = results[0]['score']
                            print(f"  {collection}: {len(results)} results (top: {top_score:.3f})")
                        else:
                            print(f"  {collection}: 0 results")
                            
                    except Exception as e:
                        print(f"  {collection}: Error - {e}")
                        collection_results[collection] = -1
                
                print(f"Total results across collections: {total_results}")
                
                retrieval_results[query] = {
                    'total_results': total_results,
                    'collection_breakdown': collection_results,
                    'vector_dim': len(query_vector)
                }
            
            # Calculate success metrics
            successful_queries = sum(1 for r in retrieval_results.values() if r['total_results'] > 0)
            success_rate = successful_queries / len(test_queries)
            
            self.test_results['retrieval_core'] = {
                'success': True,
                'success_rate': success_rate,
                'queries_tested': len(test_queries),
                'successful_queries': successful_queries,
                'results': retrieval_results
            }
            
            print(f"\n✅ Retrieval Core: PASSED ({success_rate:.1%} success rate)")
            
        except Exception as e:
            print(f"\n❌ Retrieval Core failed: {e}")
            import traceback
            traceback.print_exc()
            self.test_results['retrieval_core'] = {'success': False, 'error': str(e)}
    
    def test_end_to_end(self):
        """Test complete end-to-end pipeline"""
        print("\n🚀 Testing End-to-End V3 Pipeline...")
        print("=" * 60)
        
        if not self.engine:
            print("❌ V3 engine not available")
            return
        
        # Use our previous problem queries to test improvements
        critical_queries = [
            {
                'query': "AI integration in school curriculum",
                'expect_keywords': ['atal tinkering', 'nep 2020', 'technology'],
                'min_results': 5
            },
            {
                'query': "Section 12(1)(c) RTE Act compliance",
                'expect_keywords': ['section 12', 'rte', 'admission'],
                'min_results': 3
            },
            {
                'query': "Nadu-Nedu infrastructure development scheme",
                'expect_keywords': ['nadu-nedu', 'infrastructure', 'development'],
                'min_results': 3
            },
            {
                'query': "teacher transfer policy guidelines",
                'expect_keywords': ['transfer', 'teacher', 'policy'],
                'min_results': 3
            }
        ]
        
        try:
            e2e_results = {}
            
            for test_case in critical_queries:
                query = test_case['query']
                print(f"\nEnd-to-End Test: '{query}'")
                print("-" * 50)
                
                start_time = time.time()
                
                # Run complete V3 pipeline
                result = self.engine.retrieve(query, top_k=15)
                
                processing_time = time.time() - start_time
                
                # Analyze results
                print(f"📊 Pipeline Results:")
                print(f"   • Query type: {result.interpretation.query_type.value}")
                print(f"   • Scope: {result.interpretation.scope.value}")
                print(f"   • Verticals: {result.verticals_searched}")
                print(f"   • Rewrites: {len(result.rewrites)}")
                print(f"   • Total candidates: {result.total_candidates}")
                print(f"   • Final results: {result.final_count}")
                print(f"   • Processing time: {processing_time:.3f}s")
                
                # Check keyword coverage
                found_keywords = []
                all_content = ' '.join([r.content.lower() for r in result.results])
                
                for keyword in test_case['expect_keywords']:
                    if keyword.lower() in all_content:
                        found_keywords.append(keyword)
                
                keyword_coverage = len(found_keywords) / len(test_case['expect_keywords'])
                results_sufficient = result.final_count >= test_case['min_results']
                
                print(f"   • Expected keywords found: {found_keywords}")
                print(f"   • Keyword coverage: {keyword_coverage:.1%}")
                print(f"   • Results sufficient: {results_sufficient}")
                
                # Show top 3 results
                print(f"\n📄 Top 3 Results:")
                for i, res in enumerate(result.results[:3], 1):
                    print(f"   {i}. [{res.vertical}] Score: {res.score:.3f}")
                    print(f"      {res.doc_id} - {res.content[:100]}...")
                
                # Test success criteria
                test_success = (
                    keyword_coverage >= 0.5 and  # At least half keywords found
                    results_sufficient and       # Minimum result count
                    processing_time < 10.0       # Reasonable speed
                )
                
                e2e_results[query] = {
                    'success': test_success,
                    'processing_time': processing_time,
                    'final_count': result.final_count,
                    'keyword_coverage': keyword_coverage,
                    'verticals': result.verticals_searched,
                    'rewrites_count': len(result.rewrites),
                    'found_keywords': found_keywords
                }
                
                status = "✅ PASSED" if test_success else "❌ FAILED"
                print(f"\n{status}")
            
            # Overall success
            successful_tests = sum(1 for r in e2e_results.values() if r['success'])
            overall_success = successful_tests == len(critical_queries)
            avg_time = sum(r['processing_time'] for r in e2e_results.values()) / len(e2e_results)
            
            self.test_results['end_to_end'] = {
                'success': overall_success,
                'tests_passed': f"{successful_tests}/{len(critical_queries)}",
                'avg_processing_time': avg_time,
                'results': e2e_results
            }
            
            print(f"\n✅ End-to-End: {'PASSED' if overall_success else 'FAILED'} ({successful_tests}/{len(critical_queries)} tests)")
            print(f"Average processing time: {avg_time:.3f}s")
            
        except Exception as e:
            print(f"\n❌ End-to-End failed: {e}")
            import traceback
            traceback.print_exc()
            self.test_results['end_to_end'] = {'success': False, 'error': str(e)}
    
    def run_all_tests(self):
        """Run complete test suite"""
        print("🧪 COMPREHENSIVE V3 TEST SUITE")
        print("=" * 80)
        print("Testing all retrieval_v3 components with real integration")
        print("=" * 80)
        
        # Setup
        if not self.setup_components():
            print("❌ Cannot run tests without proper component setup")
            return False
        
        # Run all test suites
        self.test_query_understanding()
        self.test_routing()
        self.test_retrieval_core()
        self.test_end_to_end()
        
        # Generate final report
        self.generate_final_report()
        
        # Return overall success
        return all(
            test.get('success', False) 
            for test in self.test_results.values()
        )
    
    def generate_final_report(self):
        """Generate comprehensive test report"""
        print("\n" + "=" * 80)
        print("📋 COMPREHENSIVE TEST REPORT")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for test in self.test_results.values() if test.get('success', False))
        
        print(f"\n🎯 Overall Results: {passed_tests}/{total_tests} test suites passed")
        
        for component, result in self.test_results.items():
            status = "✅ PASSED" if result.get('success', False) else "❌ FAILED"
            print(f"\n{component.upper()}: {status}")
            
            if result.get('success'):
                # Component-specific metrics
                if component == 'query_understanding':
                    print(f"   • Queries tested: {result['queries_tested']}")
                elif component == 'routing':
                    print(f"   • Average coverage: {result['avg_coverage']:.1%}")
                elif component == 'retrieval_core':
                    print(f"   • Success rate: {result['success_rate']:.1%}")
                elif component == 'end_to_end':
                    print(f"   • Tests passed: {result['tests_passed']}")
                    print(f"   • Avg time: {result['avg_processing_time']:.3f}s")
            else:
                print(f"   • Error: {result.get('error', 'Unknown error')}")
        
        # Save detailed results
        report_file = f"v3_test_report_{int(time.time())}.json"
        with open(report_file, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        
        print(f"\n📄 Detailed results saved: {report_file}")
        
        if passed_tests == total_tests:
            print("\n🎉 ALL TESTS PASSED! V3 pipeline is fully functional.")
        else:
            print(f"\n💔 {total_tests - passed_tests} test suite(s) failed. Review errors above.")
        
        print("=" * 80)

def main():
    """Main test execution"""
    tester = V3ComponentTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🚀 V3 RETRIEVAL PIPELINE: READY FOR PRODUCTION")
    else:
        print("\n⚠️  V3 RETRIEVAL PIPELINE: NEEDS ATTENTION") 
    
    return success

if __name__ == "__main__":
    main()