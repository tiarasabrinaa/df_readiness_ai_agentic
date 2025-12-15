"""
Database services for V1 collections
"""
from .questions import QuestionsV1Service

# Singleton instances
questions = QuestionsV1Service()

__all__ = ['questions']