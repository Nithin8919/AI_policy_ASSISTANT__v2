"""
Intent Classifier V2 - Import Alias
===================================
This file provides an alias to the main intent_classifier.py for V2 components.
The actual V2 implementation is in intent_classifier.py.
"""

# Import everything from the main intent_classifier module
from .intent_classifier import (
    IntentClassifierV2,
    get_intent_classifier_v2,
    IntentSignals
)
from ..config.mode_config import QueryMode

# Re-export for V2 components
__all__ = [
    "IntentClassifierV2",
    "get_intent_classifier_v2", 
    "IntentSignals",
    "QueryMode"
]