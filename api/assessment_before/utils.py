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


def update_manager_phase_assessment_submission(
    manager: SessionManager, 
    validated_answers: List[int]
) -> None:
    """Store assessment results in session context"""
    manager.context["test_answers"] = validated_answers
    manager.context["likert_scores"] = validated_answers
    manager.context["current_phase"] = "evaluation"
    manager.context["answers"] = validated_answers

def update_manager_phase_assessment_question(
    manager: SessionManager, 
    questions: List[dict]
) -> None:
    """Store assessment questions in session context"""
    manager.context["test_questions"] = questions
    manager.context["current_phase"] = "evaluation"

def format_questions(questions_data: List[dict]) -> List[dict]:
    """Transform raw question data to API format"""
    return [{
        "question": q.get("question", ""),
        "indicator": q.get("indicator", ""),
        "level": q.get("level", "")
    } for q in questions_data]

def calculate_score(manager: SessionManager, validated_answers: List[int]) -> float:
    "Calculating score of assessment with cobit method"

    
    