"""
Database services for V2 collections
"""
from .questions import QuestionsV2Service

# Singleton instances
questions = QuestionsV2Service()

__all__ = ['questions']