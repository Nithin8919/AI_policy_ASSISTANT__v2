#!/usr/bin/env python3
"""
Debug Routing Issue
==================
Debug why we're only getting 'schemes' collection instead of 'schemes', 'go', 'legal'.
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

def debug_routing():
    """Debug the routing process step by step"""
    print("🔍 DEBUGGING ROUTING PROCESS")
    print("=" * 50)
    
    query = "I want to change school syllabus integrating AI"
    print(f"Query: '{query}'")
    
    # Test 1: Check feature flags
    print("\n📋 STEP 1: Feature Flags")
    try:
        from retrieval.config.settings import FEATURE_FLAGS
        print(f"   use_query_router_v2: {FEATURE_FLAGS.get('use_query_router_v2')}")
        print(f"   use_intent_classifier_v2: {FEATURE_FLAGS.get('use_intent_classifier_v2')}")
        print(f"   use_hybrid_search: {FEATURE_FLAGS.get('use_hybrid_search')}")
    except Exception as e:
        print(f"   ❌ Error checking feature flags: {e}")
    
    # Test 2: Check query planner components
    print("\n📋 STEP 2: Query Planner Components")
    try:
        from retrieval.query_processing.query_plan import get_query_planner
        planner = get_query_planner()
        
        print(f"   Using V2 classifier: {getattr(planner, 'using_v2_classifier', False)}")
        print(f"   Using V2 router: {getattr(planner, 'using_v2_router', False)}")
        
        # Test router directly
        print("\n   🔍 Testing Router Directly:")
        from retrieval.query_processing.entity_extractor import get_entity_extractor
        from retrieval.config.mode_config import QueryMode
        
        entity_extractor = get_entity_extractor()
        entities = entity_extractor.extract(query)
        
        if hasattr(planner, 'query_router') and hasattr(planner.query_router, 'route'):
            if planner.using_v2_router:
                # V2 router
                verticals = planner.query_router.route(query, entities, QueryMode.DEEP_THINK)
                print(f"   V2 Router result: {verticals}")
            else:
                # V1 router  
                vertical_scores = planner.query_router.route(query, entities)
                print(f"   V1 Router result: {vertical_scores}")
        
    except Exception as e:
        print(f"   ❌ Error testing planner: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Test V2 router directly
    print("\n📋 STEP 3: Direct V2 Router Test")
    try:
        from retrieval.query_processing.query_router_v2 import get_query_router_v2
        from retrieval.query_processing.entity_extractor import get_entity_extractor
        from retrieval.config.mode_config import QueryMode
        
        router_v2 = get_query_router_v2()
        entity_extractor = get_entity_extractor()
        entities = entity_extractor.extract(query)
        
        print(f"   Query: '{query}'")
        print(f"   Entities: {entities}")
        print(f"   Mode: {QueryMode.DEEP_THINK}")
        
        verticals = router_v2.route(query, entities, QueryMode.DEEP_THINK)
        print(f"   V2 Router Direct: {verticals}")
        
        # Test with enhanced query
        from retrieval.query_processing.query_enhancer import get_query_enhancer
        enhancer = get_query_enhancer()
        enhanced = enhancer.enhance(query, entities, mode="deep_think")
        
        print(f"\n   Enhanced query: '{enhanced}'")
        verticals_enhanced = router_v2.route(enhanced, entities, QueryMode.DEEP_THINK)
        print(f"   V2 Router Enhanced: {verticals_enhanced}")
        
    except Exception as e:
        print(f"   ❌ Error testing V2 router: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 4: Check the query plan creation
    print("\n📋 STEP 4: Query Plan Creation")
    try:
        from retrieval.query_processing.query_plan import get_query_planner
        
        planner = get_query_planner()
        plan = planner.plan(query)
        
        print(f"   Original query: '{plan.original_query}'")
        print(f"   Enhanced query: '{plan.enhanced_query}'")
        print(f"   Mode: {plan.mode}")
        print(f"   Mode confidence: {plan.mode_confidence}")
        print(f"   Verticals: {plan.verticals}")
        print(f"   Vertical confidences: {plan.vertical_confidences}")
        print(f"   Top K: {plan.top_k}")
        
    except Exception as e:
        print(f"   ❌ Error creating plan: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_routing()