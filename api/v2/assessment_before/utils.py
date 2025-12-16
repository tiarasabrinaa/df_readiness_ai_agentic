# ============== UTILS ==============
from typing import List, Any, Dict
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
        "enabler": q.get("enabler", ""),
        "contribution_max": q.get("contribution_max", 3),
        "options": [i for i in range(q.get("contribution_max", 4)+1)]
    } for q in questions_data]

def calculate_score(manager: SessionManager) -> Dict[str, float]:
    """Calculate and return average score from stored answers"""
    answers = manager.context.get("test_answers", [])
    questions = manager.context.get("test_questions", [])
    
    if not answers:
        raise ValueError("No answers found to calculate score")
    
    if not questions:
        raise ValueError("No questions found")
    
    if len(answers) != len(questions):
        raise ValueError("Mismatch between answers and questions count")

    # Sum contribution max per enabler
    sum_contribution_max = {
        "1. Principles, Policies, and Frameworks": 6,
        "2. Processes": 7,
        "3. Organizational Structures": 6,
        "4. Information": 6,
        "5. Culture, Ethics, and Behavior": 8,
        "6. People, Skills, and Competences": 5,
        "7. Services, Infrastructure, and Applications": 6
    }

    # Initialize scores
    score_per_enabler = {
        "1. Principles, Policies, and Frameworks": 0.0,
        "2. Processes": 0.0,
        "3. Organizational Structures": 0.0,
        "4. Information": 0.0,
        "5. Culture, Ethics, and Behavior": 0.0,
        "6. People, Skills, and Competences": 0.0,
        "7. Services, Infrastructure, and Applications": 0.0
    }

    for enabler, sum_contribution_max_per_enabler in sum_contribution_max.items():
        for i in range(len(answers)):
            question_enabler = questions[i].get("enabler", "")
            
            if question_enabler == enabler:
                max_contribution = questions[i].get("contribution_max", 3)
                answer_score_per_question = (answers[i] / sum_contribution_max_per_enabler) * 3
                score_per_enabler[enabler] += answer_score_per_question

    # Round scores
    score_per_enabler = {k: round(v, 2) for k, v in score_per_enabler.items()}
    
    return score_per_enabler

def check_maturity_level(score_per_enabler: Dict[str, float]) -> Dict[str, str]:
    """Determine maturity level per enabler based on score"""

    list_score = list(score_per_enabler.values())

    capability_requirements = {
        "maturity_1": [0, 0, 0, 0, 0, 0, 0],
        "maturity_2": [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
        "maturity_3": [2.0, 2.0, 2.0, 2.0, 1.0, 2.0, 2.0],
        "maturity_4": [2.0, 3.0, 3.0, 3.0, 3.0, 3.0, 2.0],
        "maturity_5": [3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0]
    }

    if list_score <= capability_requirements["maturity_1"]:
        return "maturity_1"
    elif list_score <= capability_requirements["maturity_2"]:
        return "maturity_2"
    elif list_score <= capability_requirements["maturity_3"]:
        return "maturity_3"
    elif list_score <= capability_requirements["maturity_4"]:
        return "maturity_4"
    elif list_score <= capability_requirements["maturity_5"]:
        return "maturity_5"
    else:
        return "unknown"