from typing import Dict, Any
from shared.session_manager import SessionManager
import resend
from config import settings
import json

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