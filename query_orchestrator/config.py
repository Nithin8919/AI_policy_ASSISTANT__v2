"""
Query Orchestrator Configuration
=================================
Configuration for orchestrator behavior, triggers, and mode settings.
"""

from typing import Dict, List, Set
from dataclasses import dataclass


@dataclass
class OrchestratorConfig:
    """Main orchestrator configuration"""
    
    # Mode defaults
    default_mode: str = "qa"
    valid_modes: Set[str] = None
    
    # Internet toggle
    internet_enabled_by_default: bool = False
    internet_always_on_modes: Set[str] = None
    
    # Theory corpus
    theory_enabled: bool = False
    theory_trigger_keywords: Set[str] = None
    
    # Timeouts (seconds)
    local_rag_timeout: float = 5.0
    internet_timeout: float = 3.0
    theory_timeout: float = 2.0
    total_timeout: float = 15.0
    
    # Result limits
    max_local_results: int = 10
    max_internet_results: int = 5
    max_theory_results: int = 3
    
    # Fusion weights (how to prioritize sources)
    local_weight: float = 1.0
    internet_weight: float = 0.3
    theory_weight: float = 0.2
    
    def __post_init__(self):
        if self.valid_modes is None:
            self.valid_modes = {"qa", "deep_think", "brainstorm"}
        
        if self.internet_always_on_modes is None:
            self.internet_always_on_modes = {"brainstorm"}
        
        if self.theory_trigger_keywords is None:
            self.theory_trigger_keywords = {
                "bloom", "vygotsky", "piaget", "montessori", "dewey",
                "pedagogy", "constructivism", "behaviorism", "cognitivism",
                "learning theory", "educational theory", "teaching method",
                "instructional design", "motivation theory", "mindset",
                "best practices", "global standards", "international comparison",
                "educational research", "learning science"
            }


# Default instance
DEFAULT_CONFIG = OrchestratorConfig()


def get_orchestrator_config() -> OrchestratorConfig:
    """Get orchestrator configuration"""
    return DEFAULT_CONFIG