# features/assessment_before/schemas.py
from typing import List, Dict, Optional
from pydantic import BaseModel, Field

# REQUEST SCHEMAS
class SubmitTestAnswersRequest(BaseModel):
    """Request body for POST /submit_test_answers"""
    answers: List[int] = Field(..., min_length=1, description="List of answers on a scale")

# RESPONSE SCHEMAS
class AssessmentQuestion(BaseModel):
    """Individual test question model"""
    contribution_max: int
    enabler: str
    indicator: str
    options: List[int]

class GetAssessmentModel(BaseModel):
    """Response data for GET /get_test_questions"""
    current_phase: str
    package: str
    session_id: str
    questions_count: int
    session_id: str
    questions: List[AssessmentQuestion]

class SubmitAnswersAssessment(BaseModel):
    """Response data for POST /submit_test_answers"""
    session_id: str
    current_phase: str
    average_score: float
    sum_contribution_max: int
    total_responses: int
    total_score: int