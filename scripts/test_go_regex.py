import re

query = "What are the key provisions in GO MS No.24 related to teacher eligibility?"

# Test the improved regex
pattern = r'(?:GO|G\.?O\.?)\s*(?:Ms\.?|Rt\.?|MS|RT)?\s*(?:No\.?|Number)?\s*(\d+)'

matches = re.findall(pattern, query, re.IGNORECASE)
print(f"Query: {query}")
print(f"Pattern: {pattern}")
print(f"Matches: {matches}")

# Test with query interpreter
import sys
import os
sys.path.insert(0, '/Users/nitin/Desktop/AP Policy Assitant Main NO BS/retrieval_v3')

from query_understanding.query_interpreter import QueryInterpreter

interpreter = QueryInterpreter()
interpretation = interpreter.interpret_query(query)

print(f"\nInterpretation:")
print(f"  Type: {interpretation.query_type}")
print(f"  Entities: {interpretation.detected_entities}")
print(f"  GO Refs: {interpretation.detected_entities.get('go_refs', 'None')}")
