import resend
from config import settings
from typing import Dict, Any
import random
import json
import logging

from shared.session_manager import SessionManager
from services.llm_service import llm_service
from .utils import merge_question_and_answer, format_next_steps_to_list, find_highest_lowest_enablers
from .prompts import build_summary_analysis_messages, build_next_steps_messages

resend.api_key = settings.MAIL_RESEND_API_KEY
logger = logging.getLogger("debug_logger")
# level logging.DEBUG untuk debug detail
logger.setLevel(logging.DEBUG)

def send_email(to: str, subject: str, body: str):
    """Send email notification using Resend"""
    try:
        params = {
            "from": "noreply@stelarea.com",
            "to": [to],
            "subject": subject,
            "html": body,
        }
        
        email = resend.Emails.send(params)
        
        print(f"Email sent successfully to {to}")
        print(f"Email ID: {email.get('id')}")
        return email
        
    except Exception as e:
        print(f"Failed to send email to {to}: {str(e)}")
        raise e
    
async def get_summary_analysis(manager: SessionManager) -> Dict[str, Any]:
    """Generate comprehensive analysis using LLM"""
    
    question_answers = merge_question_and_answer(manager)
    manager.context['question_answers'] = question_answers
    profile_description = manager.context.get('profile_description', '')
    score_enablers = manager.context.get('score_enablers', {})
    
    # Format questions and answers
    summary_prompt = build_summary_analysis_messages(question_answers, profile_description, manager.context.get('maturity_level', ''))
    summary = await llm_service.call_llm(summary_prompt)

    # Find highest and lowest enablers
    logger.info(f"Score Enablers: {score_enablers}")  # Ganti ke .info()
    print(f"[DEBUG] Score Enablers: {score_enablers}", flush=True)  # Tambah print biasa

    highest_enabler, lowest_enabler = find_highest_lowest_enablers(score_enablers)

    next_step_prompt = build_next_steps_messages(summary, lowest_enabler, manager.context.get('profile_description', ''))
    next_steps = await llm_service.call_llm(next_step_prompt)
    next_steps_formatted = format_next_steps_to_list(next_steps)
    
    # Return all analysis
    return {
        "summary_analysis": summary.strip(),
        "next_steps": next_steps_formatted,
        "highest_enabler": highest_enabler,
        "lowest_enabler": lowest_enabler
    }