import resend
from config import settings
from typing import Dict, Any
from shared.session_manager import SessionManager
from services.llm_service import llm_service
import random
from prompts import AssessmentPrompts
import json

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
    
async def evaluate_with_llm(manager: SessionManager) -> Dict[str, Any]:
    """Perform comprehensive evaluation using LLM"""
    try:
        questions = manager.context["test_questions"]
        answers = manager.context["test_answers"]
        user_profile = manager.context.get("user_profile", {}) if isinstance(manager.context.get("user_profile", {}), dict) else None
        # user_profile = ""
        # print(f"user_profile: {user_profile} (type: {type(user_profile)})")
        
        # Ensure user_profile is a dictionary
        if not isinstance(user_profile, dict):
            print("Error: user_profile is not a dictionary. Fallback to empty dictionary.")
            user_profile = ""  # Fallback to an empty dictionary
        
        # Proceed if it's a valid dictionary
        selected_package = manager.context["selected_package"]
        qa_pairs = manager.context.get("profiling_qa_pairs", {}) if isinstance(manager.context.get("profiling_qa_pairs", {}), dict) else {}
        likert_scores = manager.context.get("likert_scores", []) if isinstance(manager.context.get("likert_scores", []), list) else []
        
        selected_package = "qb_v1_000"
        qa_pairs = {}
        likert_scores = [random.randint(1, 4) for _ in range(len(questions))]  # Simulated scores


        # Calculate average score
        avg_score = sum(likert_scores) / len(likert_scores) if likert_scores else 0.0
        
        prompt = AssessmentPrompts.get_evaluation_prompt(
            user_profile, selected_package, qa_pairs, questions, answers, avg_score
        )
        
        ai_response = await llm_service.generate_response(prompt, [])
        
        # Ensure the response is not empty and contains JSON
        if ai_response and ai_response.strip().startswith("{") and ai_response.strip().endswith("}"):
            try:
                # Try parsing the JSON response
                evaluation = json.loads(ai_response)
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON response: {str(e)}")
                return {"error": "Failed to parse evaluation response"}
        else:
            print(f"Invalid or empty response from LLM: {ai_response}")
            return {"error": "No valid JSON response from LLM"}
            
        
        # Add calculated metrics
        evaluation["likert_average"] = avg_score
        evaluation["total_responses"] = len(likert_scores)
        
        return ai_response

    except Exception as e:
        print(f"Error during evaluation: {str(e)}")
        return {"error di main": str(e)}