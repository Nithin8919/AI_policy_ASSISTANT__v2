# Modes - mode configs (QA/Policy/Brainstorm/Compliance)

"""
Retrieval Modes - Predefined configurations
"""

MODES = {
    "qa": {
        "num_rewrites": 2,
        "num_hops": 1,
        "top_k": 20,
        "diversity_weight": 0.2,
    },
    
    "policy": {
        "num_rewrites": 3,
        "num_hops": 2,
        "top_k": 40,
        "diversity_weight": 0.4,
    },
    
    "deepthink": {
        "num_rewrites": 5,
        "num_hops": 2,
        "top_k": 60,
        "diversity_weight": 0.6,
    },
    
    "framework": {
        "num_rewrites": 5,
        "num_hops": 2,
        "top_k": 50,
        "diversity_weight": 0.5,
    },
    
    "brainstorm": {
        "num_rewrites": 5,
        "num_hops": 2,
        "top_k": 50,
        "diversity_weight": 0.7,
    },
    
    "compliance": {
        "num_rewrites": 2,
        "num_hops": 1,
        "top_k": 15,
        "diversity_weight": 0.1,
    }
}


def get_mode_config(mode: str):
    """Get config for a mode"""
    return MODES.get(mode, MODES["qa"])