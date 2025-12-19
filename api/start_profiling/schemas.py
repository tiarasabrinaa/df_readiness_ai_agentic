from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional

# REQUEST SCHEMAS

class SubmitAnswersRequest(BaseModel):
    """
    Request body for POST /submit_answers
    
    Supports two formats:
    - Array: {"answers": ["ans1", "ans2", ..., "ans11"]}
    - Object: {"question1": "ans1", "question2": "ans2", ..., "question11": "ans11"}
    """
    model_config = ConfigDict(extra='allow')
    
    answers: Optional[List[str]] = Field(
        None,
        description="Array of 11 answers",
        min_length=11,
        max_length=11
    )

# RESPONSE SCHEMAS

class OptionProfiling(BaseModel):
    label: str
    is_field: Optional[bool] = False

class QuestionProfilingModel(BaseModel):
    """Individual profiling question"""
    id: str = Field(..., description="Question identifier (e.g., 'question1')")
    question: str = Field(..., description="Question text in Indonesian")
    type: str = Field(..., description="Input type: text, select, number")
    options: Optional[List[OptionProfiling]] = Field(None, description="Options for select type")

class GetQuestionsData(BaseModel):
    """Response data for GET /start_profiling"""
    session_id: str = Field(..., description="Unique session identifier")
    questions: List[QuestionProfilingModel] = Field(..., description="List of profiling questions")
    total_questions: int = Field(..., description="Total number of questions")
    current_phase: str = Field(..., description="Current phase (e.g., 'profiling')")

class SubmitAnswersData(BaseModel):
    """Response data for POST /submit_answers"""
    session_id: str = Field(..., description="Session identifier")
    profile_description: str = Field(..., description="AI-generated profile description")
    selected_package: str = Field(..., description="Recommended package (e.g., 'qb_v1_000')")
    current_phase: str = Field(..., description="Updated phase (e.g., 'package_selected')")