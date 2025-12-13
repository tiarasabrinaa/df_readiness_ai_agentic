# api/profiling/utils.py
from typing import Any, Dict, List
from shared.session_manager import SessionManager
from lib.profiling_question import PROFILING_QUESTIONS, QUESTION_KEYS

def parse_answers_from_request(data: Dict) -> Dict[str, Any]:
    """Parse answers from request data in multiple formats"""
    qa_pairs = {}
    
    if 'answers' in data and isinstance(data['answers'], list):
        answers = data.get('answers', [])
        if len(answers) != len(PROFILING_QUESTIONS):
            raise ValueError(f"Please provide exactly {len(PROFILING_QUESTIONS)} answers.")
        
        for idx, answer in enumerate(answers):
            qa_pairs[f"question{idx+1}"] = answer
    
    elif any(key.startswith('question') for key in data.keys()):
        qa_pairs = {k: v for k, v in data.items() if k.startswith('question')}
        if len(qa_pairs) != len(PROFILING_QUESTIONS):
            raise ValueError(f"Please provide exactly {len(PROFILING_QUESTIONS)} question-answer pairs.")
    else:
        raise ValueError("Invalid format. Provide either an 'answers' array or 'question1'–'question11' keys.")
    
    return qa_pairs


def update_profile_from_qa(manager: SessionManager, qa_pairs: Dict[str, Any]):
    """Update user profile from Q&A pairs"""
    for i in range(1, len(PROFILING_QUESTIONS) + 1):
        question_key = f"question{i}"
        if question_key in qa_pairs:
            profile_key = QUESTION_KEYS[i - 1]
            manager.update_profile_data(profile_key, qa_pairs[question_key])


def format_profile_text(qa_pairs: Dict[str, Any], questions: List[Dict]) -> str:
    """
    Format Q&A pairs into readable profile text for LLM
    
    Args:
        qa_pairs: Dictionary of answers (e.g., {'question1': 'answer1', ...})
        questions: List of question objects with 'question' field
    Returns:
        Formatted string with Q&A pairs
    """
    profile_info = []
    
    for i, (key, answer) in enumerate(qa_pairs.items()):
        if i < len(questions):
            question_text = questions[i]["question"]
            profile_info.append(f"Q: {question_text}\nA: {answer}")
    
    return "\n\n".join(profile_info)

def update_manager_phase_profiling(manager: SessionManager, profile_description: str, qa_pairs: Dict[str, Any]):
    """Set the current phase of the session manager to 'profiling'"""
    manager.context["profile_description"] = profile_description
    manager.context["selected_package"] = "qb_v1_000"
    manager.context["current_phase"] = "package_selected"
    manager.context["profiling_qa_pairs"] = qa_pairs

    return manager
        