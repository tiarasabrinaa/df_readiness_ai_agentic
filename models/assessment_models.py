# models/assessment_models.py
class Question(BaseModel):
    level: str
    question: str
    why_matter: str

class AssessmentQuestion(BaseModel):
    id: Optional[str] = Field(alias="_id")
    level: str
    question: str
    why_matter: str
    personalized_question: Optional[str] = None
    
    class Config:
        allow_population_by_field_name = True
        json_encoders = {ObjectId: str}

class UserAnswer(BaseModel):
    question_id: str
    question_level: str
    original_question: str
    personalized_question: str
    user_answer: str
    confidence_score: Optional[int] = None
    answered_at: datetime = Field(default_factory=datetime.utcnow)

class AssessmentSession(BaseModel):
    id: Optional[str] = Field(alias="_id")
    user_id: str
    session_id: str
    status: str = "in_progress"  # in_progress, completed, abandoned
    current_level: str = "basic"
    answers: List[UserAnswer] = []
    assessment_result: Optional[Dict[str, Any]] = None
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    class Config:
        allow_population_by_field_name = True
        json_encoders = {ObjectId: str}