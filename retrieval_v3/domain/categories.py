# Categories - infra, FLN, teacher, health, safety…

"""
Domain Categories - Category definitions and keywords
"""

CATEGORIES = {
    'infrastructure': [
        'classroom', 'toilet', 'water', 'electricity', 'furniture',
        'playground', 'library', 'lab', 'building', 'construction'
    ],
    
    'safety': [
        'cctv', 'security', 'fire', 'medical', 'first aid',
        'hygiene', 'sanitation', 'fence', 'guard'
    ],
    
    'fln': [
        'literacy', 'numeracy', 'reading', 'writing', 'math',
        'foundational', 'basic skills', 'learning outcomes'
    ],
    
    'teacher': [
        'teacher', 'training', 'transfer', 'recruitment', 'tet',
        'qualification', 'professional development'
    ],
    
    'academic': [
        'curriculum', 'textbook', 'syllabus', 'assessment', 'exam',
        'evaluation', 'grades', 'pedagogy'
    ],
    
    'monitoring': [
        'udise', 'data', 'monitoring', 'reporting', 'compliance',
        'quality assurance', 'performance'
    ],
    
    'welfare': [
        'midday meal', 'scholarship', 'uniform', 'bicycle', 'hostel',
        'cwsn', 'inclusion', 'nutrition'
    ]
}


def get_category_keywords(category: str):
    """Get keywords for a category"""
    return CATEGORIES.get(category, [])
