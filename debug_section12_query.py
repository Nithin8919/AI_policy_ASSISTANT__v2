#!/usr/bin/env python3
"""
Debug script to trace how "What is Section 12?" is processed
"""

import sys
import re
from typing import Dict, List

def test_entity_extraction():
    """Test entity extraction for 'What is Section 12?'"""
    
    # Copy patterns from entity_extractor.py
    SECTION_PATTERNS = [
        re.compile(r'\bsection\s+(\d+[A-Za-z]*(?:\(\d+\))?(?:\([a-z]\))?)', re.IGNORECASE),
        re.compile(r'\bsec\.?\s+(\d+[A-Za-z]*)', re.IGNORECASE),
        re.compile(r'\bs\.?\s+(\d+[A-Za-z]*)', re.IGNORECASE)
    ]
    
    query = "What is Section 12?"
    print(f"🔍 Processing query: '{query}'")
    print("\n📊 Entity Extraction Results:")
    
    sections_found = []
    for i, pattern in enumerate(SECTION_PATTERNS):
        matches = list(pattern.finditer(query))
        for match in matches:
            sections_found.append({
                'pattern_id': i,
                'full_match': match.group(0),
                'section_number': match.group(1),
                'start': match.start(),
                'end': match.end()
            })
            print(f"  ✅ Pattern {i}: '{match.group(0)}' -> Section '{match.group(1)}'")
    
    if not sections_found:
        print("  ❌ No sections found")
        return []
    
    return sections_found

def test_intent_classification():
    """Test intent classification for 'What is Section 12?'"""
    
    query = "What is Section 12?"
    query_lower = query.lower()
    
    # Copy keywords from intent_classifier.py
    QA_KEYWORDS = {
        "what is", "define", "who is", "when was", "where is",
        "how many", "list", "show me", "section", "rule",
        "go number", "notification", "order", "judgment", "case"
    }
    
    print(f"\n🎯 Intent Classification Results:")
    print(f"Query: '{query}'")
    
    # Count QA keywords
    qa_score = 0
    qa_matches = []
    for keyword in QA_KEYWORDS:
        if keyword in query_lower:
            qa_score += 1
            qa_matches.append(keyword)
    
    print(f"  📈 QA Score: {qa_score}")
    print(f"  🎯 QA Matches: {qa_matches}")
    
    # Check for specific entities (should boost QA)
    entity_patterns = [
        r'section\s+\d+',
        r'article\s+\d+', 
        r'rule\s+\d+',
        r'go\s*[\d-]+',
        r'notification\s*no',
        r'case\s*no'
    ]
    
    entity_found = False
    for pattern in entity_patterns:
        if re.search(pattern, query_lower):
            entity_found = True
            print(f"  ✅ Specific entity found: {pattern}")
            break
    
    # Determine mode
    word_count = len(query_lower.split())
    print(f"  📝 Word count: {word_count}")
    
    if word_count <= 5 and qa_score > 0:
        mode = "QA"
        confidence = 0.9
    elif entity_found:
        mode = "QA" 
        confidence = 0.85
    else:
        mode = "QA"
        confidence = 0.6
    
    print(f"  🎯 Final Mode: {mode}")
    print(f"  📊 Confidence: {confidence}")
    
    return mode, confidence

def test_filter_building():
    """Test filter building from extracted entities"""
    
    print(f"\n🔧 Filter Building Results:")
    
    # Simulate extracted entities (from test_entity_extraction)
    entities = {
        'section': [{'normalized': '12', 'value': 'Section 12'}]
    }
    
    # Build filters (from query_enhancer.py logic)
    filters = {}
    
    # Section filter
    if 'section' in entities:
        section_values = [e['normalized'] for e in entities['section']]
        filters["section_number"] = section_values
        print(f"  ✅ section_number filter: {section_values}")
    
    print(f"  📊 Final filters: {filters}")
    
    return filters

def test_vertical_routing():
    """Test vertical routing for the query"""
    
    query = "What is Section 12?"
    query_lower = query.lower()
    
    print(f"\n🧭 Vertical Routing Results:")
    
    # Copy keywords from query_router.py
    VERTICAL_KEYWORDS = {
        "legal": [
            "act", "section", "article", "rule", "provision", "clause",
            "statute", "legislation", "amendment", "constitution",
            "legal", "law", "rights", "fundamental", "directive"
        ],
        "go": [
            "go", "government order", "notification", "circular",
            "memo", "office memorandum", "department", "directorate",
            "issued", "sanctioned", "approved", "g.o", "g.o.ms"
        ],
        "judicial": [
            "judgment", "case", "court", "petition", "writ",
            "high court", "supreme court", "tribunal", "bench",
            "petitioner", "respondent", "appeal", "ruling"
        ]
    }
    
    # Score each vertical
    scores = {}
    for vertical, keywords in VERTICAL_KEYWORDS.items():
        score = 0
        matches = []
        for keyword in keywords:
            if keyword in query_lower:
                score += 1
                matches.append(keyword)
        
        # Entity bonus (section found)
        if vertical == "legal" and "section" in query_lower:
            score += 2.0
            matches.append("entity_bonus:section")
        
        scores[vertical] = score
        if score > 0:
            print(f"  📊 {vertical}: score={score}, matches={matches}")
    
    # Determine primary vertical
    max_score = max(scores.values()) if scores.values() else 0
    primary_vertical = None
    for vertical, score in scores.items():
        if score == max_score and score > 0:
            primary_vertical = vertical
            break
    
    if not primary_vertical:
        primary_vertical = "legal"  # Default fallback
    
    print(f"  🎯 Primary vertical: {primary_vertical}")
    
    return primary_vertical, scores

def main():
    """Run complete trace of query processing"""
    
    print("🔬 QUERY PROCESSING TRACE")
    print("=" * 50)
    
    # 1. Entity Extraction
    sections = test_entity_extraction()
    
    # 2. Intent Classification  
    mode, confidence = test_intent_classification()
    
    # 3. Filter Building
    filters = test_filter_building()
    
    # 4. Vertical Routing
    primary_vertical, vertical_scores = test_vertical_routing()
    
    # 5. Summary
    print(f"\n📋 PROCESSING SUMMARY")
    print("=" * 30)
    print(f"🔍 Query: 'What is Section 12?'")
    print(f"🎯 Mode: {mode} (confidence: {confidence})")
    print(f"🧭 Primary Vertical: {primary_vertical}")
    print(f"🔧 Filters Applied: {filters}")
    print(f"📊 Vertical Scores: {vertical_scores}")
    
    print(f"\n✅ KEY FINDING:")
    print(f"The query 'What is Section 12?' generates a filter:")
    print(f"  section_number: ['12']")
    print(f"This filter is applied during Qdrant search to find chunks")
    print(f"where metadata.section_number = '12'")
    
    return {
        'mode': mode,
        'confidence': confidence,
        'primary_vertical': primary_vertical,
        'filters': filters,
        'vertical_scores': vertical_scores
    }

if __name__ == "__main__":
    main()