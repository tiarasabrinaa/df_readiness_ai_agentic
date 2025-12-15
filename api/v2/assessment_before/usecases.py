from typing import List, Dict, Any

from flask import jsonify
from api.v2.assessment_before.utils import format_questions, update_manager_phase_assessment, validate_answers, format_questions

from ..base.base_schemas import BaseResponse
from services.database import v2
from shared.session_manager import SessionManager
from shared.async_utils import run_async

def assessment_questions(manager: SessionManager) -> List[dict]:
    selected_package = manager.context.get("selected_package")
    
    # get 2 questions per enabler
    questions_data = v2.questions.get_all()
    
    questions = format_questions(questions_data)
    
    update_manager_phase_assessment(manager, questions)

    return questions

def process_assessment_submission(
    manager: SessionManager, 
    data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Process assessment submission
    
    Returns:
        Dict with: current_phase, average_score, total_responses, 
                   sum_contribution_max, total_score
    
    Raises:
        ValueError: If validation fails
    """
    # Validate phase
    if manager.context.get("current_phase") != "testing":
        raise ValueError("Please get test questions first")
    
    # Get answers
    answers = data.get('answers', [])
    
    if not isinstance(answers, list):
        raise ValueError("Answers must be a list")
    
    # Validate count
    expected_count = len(manager.context.get("test_questions", []))
    if len(answers) != expected_count:
        raise ValueError(f"Please provide exactly {expected_count} answers")
    
    # Validate and convert answers
    validated_answers = validate_answers(answers)
    
    # Calculate scores
    total_score = sum(validated_answers)
    avg_score = total_score / len(validated_answers)
    
    # Store results
    update_manager_phase_assessment(manager, validated_answers)
    
    # Return results
    return {
        "current_phase": manager.context["current_phase"],
        "average_score": round(avg_score, 2),
        "total_responses": len(validated_answers),
        "sum_contribution_max": len(validated_answers) * 4,
        "total_score": total_score
    }