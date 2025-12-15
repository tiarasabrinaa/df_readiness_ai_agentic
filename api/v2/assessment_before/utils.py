# ============== UTILS ==============
from typing import List, Any
from shared.session_manager import SessionManager

def validate_answers(answers: List[Any]) -> List[int]:
    """
    Validate and convert answers to integers (1-4)
    
    Args:
        answers: List of answer values
        
    Returns:
        List of validated integer scores
        
    Raises:
        ValueError: If any answer is invalid
    """
    validated = []
    
    for i, answer in enumerate(answers):
        try:
            score = int(answer)
        except (ValueError, TypeError):
            raise ValueError(f"Answer {i+1} must be a number")
        
        if score not in [1, 2, 3, 4]:
            raise ValueError(f"Answer {i+1} must be 1, 2, 3, or 4")
        
        validated.append(score)
    
    return validated

def update_manager_phase_assessment(
    manager: SessionManager, 
    validated_answers: List[int]
) -> None:
    """Store assessment results in session context"""
    manager.context["test_answers"] = validated_answers
    manager.context["likert_scores"] = validated_answers
    manager.context["current_phase"] = "evaluation"
    manager.context["test_questions"] = validated_answers

def format_questions(questions_data: List[dict]) -> List[dict]:
    """Transform raw question data to API format"""
    return [{
        "question": q.get("question", ""),
        "indicator": q.get("indicator", ""),
        "enabler": q.get("enabler", ""),
        "contribution_max": q.get("contribution_max", 3),
        "options": [i for i in range(q.get("contribution_max", 4)+1)]
    } for q in questions_data]

def get_3_questions_per_enabler() -> List[dict]:
    """
    Retrieve 3 questions for each enabler for quick test
    
    Returns:
        List of question dictionaries
    """
    from services.database.v2 import questions as v2_questions_service
    
    enablers = [
        "APO01", "APO02", "APO03", "APO04", "APO05",
        "BAI01", "BAI02", "BAI03", "BAI04", "BAI05",
        "DSS01", "DSS02", "DSS03", "DSS04", "DSS05"
    ]
    
    all_questions = []
    
    for enabler in enablers:
        questions = v2_questions_service.get_by_enabler(enabler, limit=3)
        all_questions.extend(questions)
    
    return all_questions