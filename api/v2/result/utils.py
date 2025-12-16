from typing import Dict, Any, List, Tuple
from shared.session_manager import SessionManager
import resend
from config import settings
import json
import re

def merge_question_and_answer(manager: SessionManager) -> Dict[str, Any]:
    """Merge questions and answers from session context"""
    questions = manager.context.get("test_questions", [])
    answers = manager.context.get("answers", [])
    
    merged = []
    for i in range(len(questions)):
        question = questions[i]
        answer = answers[i] if i < len(answers) else None
        merged.append({
            "question": question.get("question", ""),
            "indicator": question.get("indicator", ""),
            "enabler": question.get("enabler", ""),
            "contribution_max": question.get("contribution_max", 3),
            "selected_option": answer
        })
    
    return {
        "merged_questions_answers": merged
    }

def get_ringkasan_analisis(manager: SessionManager) -> str:
    """Extract summary analysis from session context"""
    evaluation = manager.context.get("final_evaluation", "")
    
    if isinstance(evaluation, str):
        try:
            evaluation_data = json.loads(evaluation)
            summary = evaluation_data.get("detailed_analysis", evaluation)
        except (json.JSONDecodeError, ValueError):
            summary = evaluation
    elif isinstance(evaluation, dict):
        summary = evaluation.get("detailed_analysis", "")
    else:
        summary = ""
    
    return summary

def get_lowest_enabler(manager: SessionManager) -> Dict[str, Any]:
    """
    Get enabler with lowest score from session context
    
    Returns:
        Dict with 'name' and 'score' keys
    """
    score_enablers = manager.context.get("score_enablers", {})
    
    # Validate data
    if not isinstance(score_enablers, dict) or not score_enablers:
        return {"name": "N/A", "score": 0.0}
    
    # Find lowest
    lowest_enabler = min(score_enablers.items(), key=lambda x: x[1])
    
    return {
        "name": lowest_enabler[0],
        "score": round(lowest_enabler[1], 2)
    }


def find_highest_lowest_enablers(score_enablers: Dict[str, float]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Find both highest and lowest enablers in one call
    
    Args:
        score_enablers: Dict of enabler names to scores
        
    Returns:
        Tuple of (highest_dict, lowest_dict)
    """
    if not isinstance(score_enablers, dict) or not score_enablers:
        default = {"name": "N/A", "score": 0.0}
        return default, default
    
    highest = max(score_enablers.items(), key=lambda x: x[1])
    lowest = min(score_enablers.items(), key=lambda x: x[1])
    
    return (
        {"name": highest[0], "score": round(highest[1], 2)},
        {"name": lowest[0], "score": round(lowest[1], 2)}
    )

def format_next_steps_to_list(next_steps_text: str) -> List[Dict[str, str]]:
    """
    Convert next steps text with numbered list to structured JSON array
    """
    # Remove markdown bold markers (**text**)
    clean_text = re.sub(r'\*\*(.*?)\*\*', r'\1', next_steps_text)
    
    # Pattern untuk detect numbered items (1., 2., 3., dll)
    pattern = r'(\d+)\.\s*(.+?)(?=\d+\.|$)'
    
    matches = re.findall(pattern, clean_text, re.DOTALL)
    
    steps = []
    for step_num, description in matches:
        # Clean up whitespace dan newlines
        clean_desc = description.strip().replace('\n', ' ')
        # Remove extra spaces
        clean_desc = re.sub(r'\s+', ' ', clean_desc)
        
        steps.append({
            "step": int(step_num),
            "description": clean_desc
        })
    
    return steps