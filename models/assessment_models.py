# models/assessment_models.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId

class Question(BaseModel):
    level: str
    question: str
    why_matter: str

class AssessmentQuestion(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={ObjectId: str}
    )
    
    id: Optional[str] = Field(default=None, alias="_id")
    level: str
    question: str
    why_matter: str
    personalized_question: Optional[str] = None

class UserAnswer(BaseModel):
    question_id: str
    question_level: str
    original_question: str
    personalized_question: str
    user_answer: str
    confidence_score: Optional[int] = None
    answered_at: datetime = Field(default_factory=datetime.utcnow)

class AssessmentSession(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={ObjectId: str}
    )
    
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str
    session_id: str
    status: str = "in_progress"  # in_progress, completed, abandoned
    current_level: str = "basic"
    answers: List[UserAnswer] = Field(default_factory=list)
    assessment_result: Optional[Dict[str, Any]] = None
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None