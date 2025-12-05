# Answer Generation Layer
# Answer builder, answer validator

"""
Answer Generation Layer
Build and validate structured answers with citations
"""

from .answer_builder import AnswerBuilder, Answer, build_answer
from .answer_validator import AnswerValidator, validate_answer

__all__ = [
    'AnswerBuilder',
    'Answer',
    'build_answer',
    'AnswerValidator',
    'validate_answer',
]











