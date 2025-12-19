# api/assessment_before/routes.py
from flask import Blueprint, request, jsonify
import logging

from ..base.base_schemas import BaseResponse
from shared.session_manager import get_or_create_session
from shared.async_utils import run_async
from .usecases import assessment_questions, process_assessment_submission
from . import assessment_before_bp_v2

from .schemas import (
    SubmitTestAnswersRequest,
    GetAssessmentModel,
    SubmitAnswersAssessment
)

logger = logging.getLogger("debug_logger")

@assessment_before_bp_v2.route('/get_quick_test_questions', methods=['GET'])
def get_quick_test_questions():
    """Get test questions based on selected package"""
    try:
        manager = get_or_create_session()
        
        # TODO: Re-enable phase validation after fixing phase management issues
        # if manager.context["current_phase"] not in ["package_selected", "testing", "evaluation"]:
        #     response = BaseResponse.error(message="Please complete profiling first")
        #     return jsonify(response.model_dump()), 400

        questions = assessment_questions(manager)

        if not questions:
            response = BaseResponse.error(
                message=f"No questions found for package: {manager.context.get('selected_package')}"
            )
            return jsonify(response.model_dump()), 404
        
        data = GetAssessmentModel(
            session_id=manager.session_id,
            package=manager.context.get("selected_package", ""),
            questions=questions,
            questions_count=len(questions),
            current_phase=manager.context["current_phase"],
            instruction="Please respond with numbers 1-4 for each question (Likert scale)"
        )
        
        response = BaseResponse.success(
            data=data,
            message="Test questions retrieved successfully"
        )
        return jsonify(response.model_dump()), 200
        
    except Exception as e:
        response = BaseResponse.error(
            message="Failed to get test questions",
            errors={"detail": str(e)}
        )
        return jsonify(response.model_dump()), 500

@assessment_before_bp_v2.route('/submit_test_answers', methods=['POST'])
def submit_test_answers():
    """Submit assessment answers and calculate scores"""
    logger.debug("=== submit_test_answers called ===")
    try:
        logger.debug("Getting or creating session...")
        manager = get_or_create_session()
        logger.debug(f"Session ID: {manager.session_id}")
        logger.debug(f"Current context: {manager.context}")
        
        if not request.is_json:
            logger.debug("Request is not JSON, returning 400")
            return jsonify(
                BaseResponse.error(message="Request must be JSON").model_dump()
            ), 400
        
        data = request.get_json()
        logger.debug(f"Received request data: {data}")
        
        try:
            logger.debug("Processing assessment submission...")
            result = process_assessment_submission(manager, data)
            logger.debug(f"Assessment result: {result}")
        except ValueError as e:
            logger.debug(f"ValueError in process_assessment_submission: {e}")
            return jsonify(
                BaseResponse.error(message=str(e)).model_dump()
            ), 400
        
        response_data = SubmitAnswersAssessment(
            session_id=manager.session_id,
            current_phase=manager.context.get("current_phase", ""),
            enablers_score=result["enablers_score"],
            maturity_level=result["maturity_level"]
        )
        logger.debug(f"Response data: {response_data}")
        
        logger.debug("=== submit_test_answers completed successfully ===")
        return jsonify(
            BaseResponse.success(
                data=response_data,
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