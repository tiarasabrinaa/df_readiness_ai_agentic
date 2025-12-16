import resend
from config import settings
from typing import Dict, Any
import random
import json

from shared.session_manager import SessionManager
from services.llm_service import llm_service
from .utils import merge_question_and_answer
from .prompts import build_summary_analysis_messages

resend.api_key = settings.MAIL_RESEND_API_KEY

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
    profile_description = manager.context.get('profile_description', '')
    score_enablers = manager.context.get('score_enablers', {})
    
    # Format questions and answers
    questions_answers_text = build_summary_analysis_messages(question_answers, profile_description)
    summary = await llm_service.call_llm(questions_answers_text)
    
    # Find highest and lowest enablers
    # highest_enabler, lowest_enabler = find_highest_lowest_enablers(score_enablers)
    

    
    # Return all analysis
    return {
        "summary_analysis": summary.strip(),
        "next_steps": summary.strip(),  # Placeholder, replace with actual next steps extraction
        "highest_enabler": summary.strip(),  # Already a dict with name & score
        "lowest_enabler": summary.strip()      # Already a dict with name & score
    }