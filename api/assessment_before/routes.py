# api/assessment_before/routes.py
from flask import Blueprint, request, jsonify
from ..base.base_schemas import BaseResponse
from shared.session_manager import get_or_create_session
from shared.async_utils import run_async
from .usecases import createResult, assessment_questions
from . import assessment_before_bp

from .schemas import (
    SubmitTestAnswersRequest,
    GetAssessmentModel,
    SubmitAnswersAssessment
)

@assessment_before_bp.route('/get_test_questions', methods=['GET'])
def get_test_questions():
    """Get test questions based on selected package"""
    try:
        manager = get_or_create_session()
        
        if manager.context["current_phase"] not in ["package_selected", "testing"]:
            response = BaseResponse.error(message="Please complete profiling first")
            return jsonify(response.model_dump()), 400

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

@assessment_before_bp.route('/submit_test_answers', methods=['POST'])
def submit_test_answers():
    try:
        manager = get_or_create_session()
        
        if manager.context["current_phase"] != "testing":
            response = BaseResponse.error(message="Please get test questions first")
            return jsonify(response.model_dump()), 400
        
        data = request.get_json()
        answers = data.get('answers', [])
        
        if not isinstance(answers, list):
            response = BaseResponse.error(message="Answers must be a list")
            return jsonify(response.model_dump()), 400
        
        expected_count = len(manager.context["test_questions"])
        if len(answers) != expected_count:
            response = BaseResponse.error(
                message=f"Please provide exactly {expected_count} answers"
            )
            return jsonify(response.model_dump()), 400
        
        validated_answers = []
        for i, answer in enumerate(answers):
            try:
                score = int(answer)
                if score not in [1, 2, 3, 4]:
                    response = BaseResponse.error(
                        message=f"Answer {i+1} must be 1, 2, 3, or 4"
                    )
                    return jsonify(response.model_dump()), 400
                validated_answers.append(score)
            except (ValueError, TypeError):
                response = BaseResponse.error(
                    message=f"Answer {i+1} must be a number"
                )
                return jsonify(response.model_dump()), 400
        
        manager.context["test_answers"] = validated_answers
        manager.context["likert_scores"] = validated_answers
        manager.context["current_phase"] = "evaluation"
        
        avg_score = createResult.calculate_likert_average(validated_answers)
        
        data = SubmitAnswersAssessment(
            session_id=manager.session_id,
            current_phase=manager.context["current_phase"],
            average_score=round(avg_score, 2),
            total_responses=len(validated_answers),
            sum_contribution_max=len(validated_answers) * 4,
            total_score=sum(validated_answers)
        )
        
        response = BaseResponse.success(
            data=data,
            message="Answers submitted successfully"
        )
        return jsonify(response.model_dump()), 200
        
    except Exception as e:
        response = BaseResponse.error(
            message="Failed to submit answers",
            errors={"detail": str(e)}
        )
        return jsonify(response.model_dump()), 500