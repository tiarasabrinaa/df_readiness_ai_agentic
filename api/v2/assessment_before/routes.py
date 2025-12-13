# api/assessment_before/routes.py
from flask import Blueprint, request, jsonify
from ...base.base_schemas import BaseResponse
from shared.session_manager import get_or_create_session
from .usecases import CalculateScore
from services.database_service import db_service_v2
from .schemas import (
    QuestionResponse,
    TestQuestionsData,
    SubmitAnswersRequest,
    AnswerDetail,
    SubmitAnswersData
)
from . import assessment_before_bp

@assessment_before_bp.route('/get_test_questions', methods=['GET'])
def get_test_questions():
    """Get test questions based on selected package"""
    try:
        manager = get_or_create_session()
        
        if manager.context["current_phase"] not in ["package_selected", "testing"]:
            response = BaseResponse.error(message="Please complete profiling first")
            return jsonify(response.model_dump()), 400
        
        selected_package = "qb_v2_000"
        
        questions_data = db_service_v2.get_questions_by_package_sync(selected_package, limit=15)
        
        if not questions_data:
            response = BaseResponse.error(
                message=f"No questions found for package: {selected_package}"
            )
            return jsonify(response.model_dump()), 404
        
        sum_contribution_max = sum(q.get("contribution_max", 4) for q in questions_data)
        
        questions = []
        for q in questions_data:
            contribution_max = q.get("contribution_max", 4)
            
            question = QuestionResponse(
                question=q.get("question", ""),
                indicator=q.get("indicator", ""),
                enabler=q.get("enabler", ""),
                contribution_max=contribution_max,
                options=list(range(1, contribution_max + 1))
            )
            questions.append(question)
        
        manager.context["test_questions"] = [q.model_dump() for q in questions]
        manager.context["sum_contribution_max"] = sum_contribution_max
        manager.context["current_phase"] = "testing"
        
        response_data = TestQuestionsData(
            session_id=manager.session_id,
            package=selected_package,
            questions=questions,
            questions_count=len(questions),
            current_phase=manager.context["current_phase"],
            instruction="Please respond with numbers according to each question's options"
        )
        
        response = BaseResponse.success(
            data=response_data.model_dump(),
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
    """Submit test answers with contribution-based scoring"""
    try:
        manager = get_or_create_session()

        if manager.context["current_phase"] != "testing":
            response = BaseResponse.error(message="Please get test questions first")
            return jsonify(response.model_dump()), 400

        if not request.is_json:
            response = BaseResponse.error(message="Request must be JSON")
            return jsonify(response.model_dump()), 400

        try:
            request_data = SubmitAnswersRequest(**request.get_json())
            request_data.validate(manager.context.get("test_questions", []))
        except Exception as e:
            response = BaseResponse.error(
                message="Invalid request data",
                errors={"detail": str(e)}
            )
            return jsonify(response.model_dump()), 400

        answers = request_data.answers
        contribution_max = request_data.contribution_max
        test_questions = manager.context.get("test_questions", [])
        sum_contribution_max = manager.context.get("sum_contribution_max", 0)

        answer_details = []
        total_score = 0

        for i, answer in enumerate(answers):
            question = test_questions[i]
            
            max_score = question["contribution_max"]

            if answer < 1 or answer > max_score:
                response = BaseResponse.error(
                    message=f"Answer for question {i+1} must be between 1 and {max_score}"
                )
                return jsonify(response.model_dump()), 400

            score = (max_score / answer) * sum_contribution_max
            total_score += score

            answer_details.append(AnswerDetail(
                answer=answer,
                contribution_max=max_score,
                score=score
            ))

        average_score = total_score / len(answers)

        response_data = SubmitAnswersData(
            session_id=manager.session_id,
            current_phase=manager.context["current_phase"],
            answers=answer_details,
            sum_contribution_max=sum_contribution_max,
            total_score=total_score,
            average_score=average_score,
            total_responses=len(answers)
        )

        response = BaseResponse.success(
            data=response_data.model_dump(),
            message="Answers submitted successfully"
        )
        return jsonify(response.model_dump()), 200

    except Exception as e:
        response = BaseResponse.error(
            message="Failed to submit answers",
            errors={"detail": str(e)}
        )
        return jsonify(response.model_dump()), 500
