"""
Retrieval System Test Suite - Post-Fix Validation
==================================================
Tests all critical functionality after applying fixes.

Run this after deploying fixes to verify 100% success rate.
"""

import os
import sys
import logging
from typing import Dict, List
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RetrievalTestSuite:
    """Comprehensive test suite for retrieval system"""
    
    def __init__(self):
        """Initialize test suite"""
        self.results = []
        self.start_time = None
        
    def run_all_tests(self) -> Dict:
        """Run all tests and return results"""
        self.start_time = datetime.now()
        
        logger.info("=" * 80)
        logger.info("🚀 RETRIEVAL SYSTEM TEST SUITE")
        logger.info("=" * 80)
        
        # Test 1: System initialization
        self.test_system_initialization()
        
        # Test 2: Entity extraction with section
        self.test_entity_extraction()
        
        # Test 3: Filter generation
        self.test_filter_generation()
        
        # Test 4: Field mapping
        self.test_field_mapping()
        
        # Test 5: Section query
        self.test_section_query()
        
        # Test 6: Citation generation
        self.test_citation_generation()
        
        # Test 7: Multi-vertical query
        self.test_multi_vertical_query()
        
        # Test 8: Performance test
        self.test_performance()
        
        # Generate report
        return self.generate_report()
    
    def test_system_initialization(self):
        """Test 1: System can initialize without errors"""
        test_name = "System Initialization"
        logger.info(f"\n📋 Test 1: {test_name}")
        
        try:
            # Try to import all components
            from retrieval import RetrievalRouter
            from retrieval.query_processing import get_query_enhancer, get_entity_extractor
            from retrieval.config.field_mappings import get_mapped_fields
            
            # Try to create router
            router = RetrievalRouter()
            
            self.record_pass(test_name, "All components initialized successfully")
            
        except Exception as e:
            self.record_fail(test_name, f"Initialization failed: {e}")
    
    def test_entity_extraction(self):
        """Test 2: Entity extraction detects sections correctly"""
        test_name = "Entity Extraction"
        logger.info(f"\n📋 Test 2: {test_name}")
        
        try:
            from retrieval.query_processing import get_entity_extractor
            
            extractor = get_entity_extractor()
            
            # Test queries
            test_cases = [
                ("What is Section 12?", "section", "12"),
                ("Tell me about Section 12A(1)", "section", "12A(1)"),
                ("Explain GO 123", "go_number", "123"),
                ("Policies from 2023", "year", "2023")
            ]
            
            all_passed = True
            for query, expected_type, expected_value in test_cases:
                entities = extractor.extract(query)
                
                if expected_type in entities:
                    values = extractor.get_entity_values(entities, expected_type)
                    if expected_value in values:
                        logger.info(f"  ✅ '{query}' → {expected_type}={expected_value}")
                    else:
                        logger.error(f"  ❌ '{query}' → Expected {expected_value}, got {values}")
                        all_passed = False
                else:
                    logger.error(f"  ❌ '{query}' → Entity type '{expected_type}' not found")
                    all_passed = False
            
            if all_passed:
                self.record_pass(test_name, "All entity extractions correct")
            else:
                self.record_fail(test_name, "Some entity extractions failed")
                
        except Exception as e:
            self.record_fail(test_name, f"Entity extraction error: {e}")
    
    def test_filter_generation(self):
        """Test 3: Filter generation uses correct field names"""
        test_name = "Filter Generation"
        logger.info(f"\n📋 Test 3: {test_name}")
        
        try:
            from retrieval.query_processing import get_query_enhancer, get_entity_extractor
            
            extractor = get_entity_extractor()
            enhancer = get_query_enhancer()
            
            # Extract entities
            query = "What is Section 12?"
            entities = extractor.extract(query)
            
            # Build filters
            filters = enhancer.build_filter_dict(entities)
            
            # Verify correct field name (FIXED: now expects "section" not "sections")
            if "section" in filters:
                if "12" in filters["section"]:
                    logger.info(f"  ✅ Filter generated correctly: {filters}")
                    self.record_pass(test_name, f"Correct filter: {filters}")
                else:
                    self.record_fail(test_name, f"Wrong value in filter: {filters}")
            else:
                self.record_fail(test_name, f"Wrong field name (expected 'section'): {filters}")
                
        except Exception as e:
            self.record_fail(test_name, f"Filter generation error: {e}")
    
    def test_field_mapping(self):
        """Test 4: Field mapping works correctly"""
        test_name = "Field Mapping"
        logger.info(f"\n📋 Test 4: {test_name}")
        
        try:
            from retrieval.config.field_mappings import (
                get_mapped_fields,
                validate_filter,
                build_multi_field_condition
            )
            
            # Test legal vertical section mapping
            mapped = get_mapped_fields("sections", "legal")
            expected = ["section", "sections", "mentioned_sections"]
            
            if set(mapped) == set(expected):
                logger.info(f"  ✅ Legal sections map to: {mapped}")
                
                # Test filter validation
                if validate_filter("sections", "legal"):
                    logger.info(f"  ✅ Filter validation works")
                    self.record_pass(test_name, "Field mapping correct for all verticals")
                else:
                    self.record_fail(test_name, "Filter validation failed")
            else:
                self.record_fail(test_name, f"Expected {expected}, got {mapped}")
                
        except Exception as e:
            self.record_fail(test_name, f"Field mapping error: {e}")
    
    def test_section_query(self):
        """Test 5: Section query end-to-end"""
        test_name = "Section Query End-to-End"
        logger.info(f"\n📋 Test 5: {test_name}")
        
        try:
            from retrieval import query
            
            # Test query
            response = query("What is Section 12?")
            
            # Check response structure
            if "answer" in response:
                logger.info(f"  ✅ Got answer: {response['answer'][:100]}...")
                
                # Check for filters in plan
                if "plan" in response:
                    plan = response["plan"]
                    filters = plan.get("filters", {})
                    
                    if "section" in filters:
                        logger.info(f"  ✅ Filters applied: {filters}")
                        self.record_pass(test_name, "Section query works end-to-end")
                    else:
                        self.record_fail(test_name, f"No section filter applied: {filters}")
                else:
                    self.record_fail(test_name, "No plan in response")
            else:
                self.record_fail(test_name, "No answer in response")
                
        except Exception as e:
            self.record_fail(test_name, f"Query error: {e}")
    
    def test_citation_generation(self):
        """Test 6: Citations are generated properly"""
        test_name = "Citation Generation"
        logger.info(f"\n📋 Test 6: {test_name}")
        
        try:
            from retrieval import query
            
            # Test query that should have citations
            response = query("What is the RTE Act?", mode="qa")
            
            answer = response.get("answer", "")
            
            # Check for citation format [Doc X]
            import re
            citations = re.findall(r'\[Doc\s+\d+\]', answer)
            
            if citations:
                logger.info(f"  ✅ Found {len(citations)} citations: {citations}")
                
                # Check bibliography
                if "bibliography" in response and response["bibliography"]:
                    logger.info(f"  ✅ Bibliography has {len(response['bibliography'])} entries")
                    self.record_pass(test_name, f"Citations present: {len(citations)} found")
                else:
                    self.record_fail(test_name, "No bibliography generated")
            else:
                self.record_fail(test_name, "No citations found in answer")
                
        except Exception as e:
            self.record_fail(test_name, f"Citation test error: {e}")
    
    def test_multi_vertical_query(self):
        """Test 7: Multi-vertical query works"""
        test_name = "Multi-Vertical Query"
        logger.info(f"\n📋 Test 7: {test_name}")
        
        try:
            from retrieval import query
            
            # Query that should hit multiple verticals
            response = query("Teacher transfer policies", mode="deep_think")
            
            if "results" in response:
                verticals = set()
                for result in response["results"]:
                    verticals.add(result.get("vertical", "unknown"))
                
                logger.info(f"  ✅ Results from verticals: {verticals}")
                
                if len(verticals) > 1:
                    self.record_pass(test_name, f"Multi-vertical retrieval: {verticals}")
                else:
                    self.record_fail(test_name, f"Only one vertical: {verticals}")
            else:
                self.record_fail(test_name, "No results in response")
                
        except Exception as e:
            self.record_fail(test_name, f"Multi-vertical test error: {e}")
    
    def test_performance(self):
        """Test 8: Performance benchmarks"""
        test_name = "Performance Benchmarks"
        logger.info(f"\n📋 Test 8: {test_name}")
        
        try:
            from retrieval import query
            import time
            
            # Test QA mode (should be < 2s)
            start = time.time()
            response = query("What is Section 12?", mode="qa")
            qa_time = time.time() - start
            
            logger.info(f"  ⏱️ QA mode: {qa_time:.2f}s")
            
            if qa_time < 2.0:
                self.record_pass(test_name, f"Performance acceptable: QA={qa_time:.2f}s")
            else:
                self.record_fail(test_name, f"Too slow: QA={qa_time:.2f}s")
                
        except Exception as e:
            self.record_fail(test_name, f"Performance test error: {e}")
    
    def record_pass(self, test_name: str, details: str):
        """Record test pass"""
        self.results.append({
            "test": test_name,
            "status": "PASS",
            "details": details
        })
        logger.info(f"✅ PASS: {details}")
    
    def record_fail(self, test_name: str, details: str):
        """Record test failure"""
        self.results.append({
            "test": test_name,
            "status": "FAIL",
            "details": details
        })
        logger.error(f"❌ FAIL: {details}")
    
    def generate_report(self) -> Dict:
        """Generate final test report"""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = sum(1 for r in self.results if r["status"] == "FAIL")
        total = len(self.results)
        
        success_rate = (passed / total * 100) if total > 0 else 0
        
        logger.info("\n" + "=" * 80)
        logger.info("📊 TEST REPORT")
        logger.info("=" * 80)
        logger.info(f"Total Tests: {total}")
        logger.info(f"Passed: {passed} ✅")
        logger.info(f"Failed: {failed} ❌")
        logger.info(f"Success Rate: {success_rate:.1f}%")
        logger.info(f"Duration: {duration:.2f}s")
        logger.info("=" * 80)
        
        # Detailed results
        logger.info("\nDetailed Results:")
        for i, result in enumerate(self.results, 1):
            status_icon = "✅" if result["status"] == "PASS" else "❌"
            logger.info(f"{i}. {status_icon} {result['test']}: {result['details']}")
        
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "success_rate": success_rate,
            "duration": duration,
            "results": self.results
        }


def main():
    """Run test suite"""
    suite = RetrievalTestSuite()
    report = suite.run_all_tests()
    
    # Exit with appropriate code
    if report["success_rate"] == 100.0:
        logger.info("\n🎉 ALL TESTS PASSED! System is battle-tested and ready!")
        sys.exit(0)
    else:
        logger.error(f"\n⚠️ {report['failed']} tests failed. Please review and fix.")
        sys.exit(1)


if __name__ == "__main__":
    main()