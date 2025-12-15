"""
Database services
Organized by version (v1, v2)

Usage:
    from services.database import v1, v2
    
    # V1 questions
    questions = v1.questions.get_by_package("qb_v1_000")
    
    # V2 questions
    questions = v2.questions.get_by_enabler("APO01")
"""
from . import v1
from . import v2

# Backward compatibility - default to v1
db_service = v2.questions

__all__ = ['v1', 'v2', 'db_service']