import os
from typing import List

class CollectionResolver:
    """Centralized collection name resolution"""
    
    MAPPINGS = {
        'go': 'ap_government_orders',
        'legal': 'ap_legal_documents',
        'judicial': 'ap_judicial_documents',
        'schemes': 'ap_schemes',
        'reports': 'ap_data_reports'
    }
    
    @classmethod
    def resolve(cls, vertical: str) -> str:
        """Get collection name for vertical"""
        env = os.getenv('ENVIRONMENT', 'production')
        name = cls.MAPPINGS.get(vertical, cls.MAPPINGS['go'])
        
        if env == 'staging':
            return f"staging_{name}"
        return name
    
    @classmethod
    def get_all(cls) -> List[str]:
        """Get all collection names"""
        return [cls.resolve(v) for v in cls.MAPPINGS.keys()]
    
    @classmethod
    def reverse_lookup(cls, collection_name: str) -> str:
        """Get vertical from collection name"""
        for vertical, name in cls.MAPPINGS.items():
            if name in collection_name:
                return vertical
        return 'go'
