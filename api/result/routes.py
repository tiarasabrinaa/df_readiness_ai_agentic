from flask import request, jsonify
from shared.session_manager import get_or_create_session, async_route
from datetime import datetime

from .usecases import evaluate_with_llm, send_email
from ..base.base_schemas import BaseResponse
from .schemas import EmailRequest, EmailResponse

from email_template import generate_email_template


from . import result

@result.route('/submit_email', methods=['POST'])
def submit_email():
    """Submit user email for notifications"""
    try:
        manager = get_or_create_session()
        
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
        
        data = request.get_json()
        email = data.get('email')
        
        if not email or '@' not in email:
            return jsonify({"error": "Invalid email address"}), 400
        
        manager.context["user_profile"]["email"] = email
        
        data = EmailResponse (
            session_id=manager.context.get("session_id", ""),
            email=email,
            message="Email submitted successfully"
        )
    
        response = BaseResponse.success(
            data=data,
            message="Email submitted successfully"
        )
        return jsonify(response.model_dump()), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@result.route('/get_results', methods=['GET'])
@async_route
async def get_results():
    """Get final evaluation and recommendations using LLM"""
    import json 
    
    try:
        manager = get_or_create_session()
        
        current_phase = manager.context.get('current_phase')
        print(f"Current phase: {current_phase}")
        
        if current_phase == "evaluation":
            print("Performing LLM evaluation...")
            evaluation = await evaluate_with_llm(manager)
            
            manager.context["final_evaluation"] = evaluation
            manager.context["current_phase"] = "completed"

            user_profile = manager.context.get("user_profile", {})
            
            if not isinstance(user_profile, dict):
                if isinstance(user_profile, str):
                    try:
                        user_profile = json.loads(user_profile)
                    except (json.JSONDecodeError, ValueError):
                        user_profile = {}
                else:
                    user_profile = {}

            user_email = user_profile.get("email") if isinstance(user_profile, dict) else None

            if user_email:
                email_subject = "Digital Forensic Readiness (DFR) Test Results"
                email_body = generate_email_template(manager)
                try:
                    print(f"Sending email to: {user_email}")
                    send_email(user_email, email_subject, email_body)
                    print("Email sent successfully")
                except Exception as e:
                    print(f"Failed to send email: {str(e)}")
            else:
                print("Email not provided.")
                return jsonify({
                    "error": "Email not provided. Please submit your email to receive results."
                })
            
            evaluation = manager.context["final_evaluation"]
            if isinstance(evaluation, str):
                try:
                    evaluation = json.loads(evaluation)
                except (json.JSONDecodeError, ValueError):
                    evaluation = {"detailed_analysis": evaluation}
            
            data = {
                "session_id": manager.session_id,
                "selected_package": manager.context.get("selected_package"),
                "profile_description": manager.context.get("profile_description"),
                "user_profile": user_profile,
                "profiling_qa": manager.context.get("profiling_qa_pairs", {}),
                "test_questions": len(manager.context.get("test_questions", [])),
                "evaluation": evaluation,  # Now parsed as object
                "questions_answered": len(manager.context.get("test_answers", [])),
                "current_phase": manager.context["current_phase"],
                "assessment_complete": True,
                "timestamp": datetime.now().isoformat()
            }

            return BaseResponse.success(
                data=data,
                message="Results retrieved successfully"
            )
            
        elif current_phase == "completed":
            user_profile = manager.context.get("user_profile", {})
            
            if not isinstance(user_profile, dict):
                if isinstance(user_profile, str):
                    try:
                        user_profile = json.loads(user_profile)
                    except (json.JSONDecodeError, ValueError):
                        user_profile = {}
                else:
                    user_profile = {}
            
            evaluation = manager.context.get("final_evaluation")
            if isinstance(evaluation, str):
                try:
                    evaluation = json.loads(evaluation)
                except (json.JSONDecodeError, ValueError):
                    evaluation = {"detailed_analysis": evaluation}
            
            data = {
                "session_id": manager.session_id,
                "selected_package": manager.context.get("selected_package"),
                "profile_description": manager.context.get("profile_description"),
                "user_profile": user_profile,
                "profiling_qa": manager.context.get("profiling_qa_pairs", {}),
                "test_questions": len(manager.context.get("test_questions", [])),
                "evaluation": evaluation,
                "questions_answered": len(manager.context.get("test_answers", [])),
                "current_phase": current_phase,
                "assessment_complete": True,
                "timestamp": datetime.now().isoformat()
            }

            return BaseResponse.success(
                data=data,
                message="Results retrieved successfully"
            )

        else:
            print("Test answers not submitted.")
            return jsonify({"error": "Please submit test answers first"}), 400
        
    except Exception as e:
        print(f"Error in get_results: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error in get_results": str(e)}), 500