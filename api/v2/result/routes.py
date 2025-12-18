from flask import request, jsonify
from shared.session_manager import get_or_create_session, async_route
from shared.async_utils import run_async
from datetime import datetime
import logging

from .usecases import send_email
from ..base.base_schemas import BaseResponse
from .schemas import EmailRequest, EmailResponse, SummaryAnalysisResponse
from .usecases import get_summary_analysis
from email_template import generate_email_template

from . import result_v2

logger = logging.getLogger("debug_logger")

@result_v2.route('/submit_email', methods=['POST'])
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
    
@result_v2.route('/get_results', methods=['GET'])
def get_results():
    """Get final evaluation and recommendations using LLM"""
    import json 
    
    try:
        manager = get_or_create_session()
        
        current_phase = manager.context.get('current_phase')
        print(f"Current phase: {current_phase}")
        
        if current_phase == "evaluation":
            print("Performing LLM evaluation...")
        
        analysis = {}
        analysis = run_async(get_summary_analysis(manager))

        data = {
            "score_per_enablers": manager.context.get("score_enablers", {}),
            "maturity_level": manager.context.get("maturity_level", ""),
            "summary_analysis": analysis["summary_analysis"],
            "next_steps": analysis["next_steps"],
            "highest_enabler": analysis["highest_enabler"],
            "lowest_enabler": analysis["lowest_enabler"]
        }

        return jsonify(
            BaseResponse.success(
                data=data,
                message="Answers submitted successfully"
            ).model_dump()
        ), 200

    except Exception as e:
        logger.error(f"Error in submit_test_answers: {e}", exc_info=True)
        return jsonify(
            BaseResponse.error(
                message="Failed to submit answers",
                errors=str(e)
            ).model_dump()
        ), 500


    