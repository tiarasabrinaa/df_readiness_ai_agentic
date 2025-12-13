from typing import List
from api.assessment_before.utils import update_manager_phase_assessment

from ..base.base_schemas import BaseResponse
from services.database_service import db_service
from shared.session_manager import SessionManager
from shared.async_utils import run_async

class createResult:
    def calculate_likert_average(self, scores: List[int]) -> float:
        """Calculate average of Likert scale responses"""
        if not scores:
            return 0.0
        
        valid_scores = [score for score in scores if isinstance(score, int) and 1 <= score <= 4]
        if not valid_scores:
            return 0.0
        
        return sum(valid_scores) / len(valid_scores)
    
createResult = createResult()

def assessment_questions(manager: SessionManager) -> List[dict]:
    """Retrieve assessment questions based on selected package"""

    selected_package = manager.context.get("selected_package")
    
    questions_data = run_async(
        db_service.get_questions_by_package(selected_package, limit=15)
    )
        
    questions = []
    for q in questions_data:
        questions.append({
            "question": q.get("question", ""),
            "indicator": q.get("indicator", ""),
            "level": q.get("level", "")
        })

    update_manager_phase_assessment(manager, questions)

    return questions