from typing import List, Dict, Any

from flask import jsonify
from api.v2.assessment_before.utils import format_questions, update_manager_phase_assessment_question, update_manager_phase_assessment_submission, validate_answers, format_questions, calculate_score, check_maturity_level

from ..base.base_schemas import BaseResponse
from services.database import v2
from shared.session_manager import SessionManager
from shared.async_utils import run_async

def assessment_questions(manager: SessionManager) -> List[dict]:
    selected_package = manager.context.get("selected_package")
    
    # get 2 questions per enabler
    questions_data = v2.questions.get_questions_per_enabler()
    
    questions = format_questions(questions_data)
    
    update_manager_phase_assessment_question(manager, questions)

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
    # TODO: Re-enable phase validation after fixing phase management issues
    # Validate phase
    # if manager.context.get("current_phase") != "evaluation":
    #     raise ValueError("Please get test questions first")
    
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

    update_manager_phase_assessment_submission(manager, validated_answers)

    enablers_score = calculate_score(manager)
    manager.context["score_enablers"] = enablers_score

    maturity_level = check_maturity_level(enablers_score)
    manager.context["maturity_level"] = maturity_level
    
    # Return results
    return {
        "enablers_score": enablers_score,
        "maturity_level": maturity_level
    }