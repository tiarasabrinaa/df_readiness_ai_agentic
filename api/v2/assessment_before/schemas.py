from typing import List, Optional
from pydantic import BaseModel, Field

class QuestionResponse(BaseModel):
    question: str
    indicator: str
    enabler: str
    contribution_max: int
    options: List[int]

class TestQuestionsData(BaseModel):
    session_id: str
    package: str
    questions: List[QuestionResponse]
    questions_count: int
    current_phase: str
    instruction: str

class AnswerItem(BaseModel):
    question_index: int
    answer: int
    contribution_max: int

class SubmitAnswersRequest(BaseModel):
    answers: List[int] = Field(..., min_length=1, description="Answer values")
    contribution_max: Optional[List[int]] = Field(None, description="Contribution max values for each question")
    
    def validate(self, test_questions: list):
        # Ensure that the number of answers matches the number of questions
        if len(self.answers) != len(test_questions):
            raise ValueError(f"Number of answers must be equal to number of questions. Expected {len(test_questions)} answers.")

        # If contribution_max is provided, validate its length matches the number of questions
        if self.contribution_max and len(self.contribution_max) != len(test_questions):
            raise ValueError(f"Number of contribution_max values must match the number of questions. Expected {len(test_questions)} values.")
        
        # If contribution_max is not provided, we will use the values from test_questions
        if not self.contribution_max:
            # Use the contribution_max values from the questions (handle both dict and object)
            self.contribution_max = [
                q.get("contribution_max", 4) if isinstance(q, dict) else q.contribution_max 
                for q in test_questions
            ]

class AnswerDetail(BaseModel):
    answer: int
    contribution_max: int
    score: float 

class SubmitAnswersData(BaseModel):
    session_id: str
    current_phase: str
    answers: List[AnswerDetail]
    sum_contribution_max: int
    total_score: float
    average_score: float
    total_responses: int
