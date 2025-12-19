from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from shared.session_manager import get_or_create_session, async_route
from ..base.base_schemas import BaseResponse
from .schemas import (
    SubmitAnswersRequest,
    GetQuestionsData,
    SubmitAnswersData,
    QuestionProfilingModel
)
from .utils import parse_answers_from_request, update_profile_from_qa
from .usecases import generate_profile_description
from lib.profiling_question import PROFILING_QUESTIONS
import logging

from . import start_profiling_bp

logger = logging.getLogger("debug_logger")

@start_profiling_bp.route('/start_profiling', methods=['GET'])
def get_profiling_questions():
    """
    Get profiling questions for cybersecurity assessment
    
    Returns:
        BaseResponse[GetQuestionsData]: Session info and list of questions
        
    Response Example:
        {
            "status": "success",
            "message": "Profiling questions retrieved successfully",
            "data": {
                "session_id": "sess_abc123",
                "questions": [
                    {
                        "id": "question1",
                        "question": "Apa industri organisasi Anda?",
                        "type": "select",
                        "options": ["Tech", "Finance", ...]
                    },
                    ...
                ],
                "total_questions": 11,
                "current_phase": "profiling"
            }
        }
    """
    try:
        manager = get_or_create_session()
        
        questions = [
            QuestionProfilingModel(**q) if isinstance(q, dict) else q 
            for q in PROFILING_QUESTIONS
        ]
        
        # Build response data
        data = GetQuestionsData(
            session_id=manager.session_id,
            questions=questions,
            total_questions=len(PROFILING_QUESTIONS),
            current_phase=manager.context.get("current_phase", "profiling")
        )
        
        response = BaseResponse[GetQuestionsData].success(
            data=data,
            message="Profiling questions retrieved successfully"
        )
        
        return jsonify(response.model_dump(exclude_none=True))

    except Exception as e:
        response = BaseResponse.error(
            message="Failed to retrieve profiling questions",
            errors=str(e)
        )
        return jsonify(response.model_dump(exclude_none=True)), 500


@start_profiling_bp.route('/submit_answers', methods=['POST'])
@async_route
async def submit_answers():
    """
    Submit profiling answers and generate AI profile description
    
    Request Body:
        SubmitAnswersRequest (see schemas.py)
        - Format 1 (array): {"answers": ["ans1", "ans2", ..., "ans11"]}
        - Format 2 (object): {"question1": "ans1", "question2": "ans2", ...}
        
    Returns:
        BaseResponse[SubmitAnswersData]: Profile description and recommendations
        
    Request Example:
        {
            "answers": [
                "Teknologi Informasi",
                "50-100 karyawan",
                "Direktur IT",
                "5 tahun",
                "S1 Teknik Informatika",
                "Ya",
                "Tidak",
                "Kurang dari 1 miliar",
                "Reguler",
                "3-6 bulan",
                "Ya"
            ]
        }
        
    Response Example:
        {
            "status": "success",
            "message": "Answers submitted successfully",
            "data": {
                "session_id": "sess_abc123",
                "profile_description": "Organisasi teknologi menengah...",
                "selected_package": "qb_v1_000",
                "current_phase": "package_selected"
            }
        }
    """

    try:
        submit_request = SubmitAnswersRequest(**request.get_json())
    except ValidationError as e:
        response = BaseResponse.error(
            message="Validation error",
            errors=e
        )
        return jsonify(response.model_dump(exclude_none=True)), 400
        
    try:
        manager = get_or_create_session()
        profile_description = await generate_profile_description(
            manager=manager,
            answer_submission=submit_request.model_dump(),
            questions=PROFILING_QUESTIONS
        )

        # Check if AI system is unavailable
        if "sistem AI sedang tidak tersedia" in profile_description or "sistem AI tidak tersedia" in profile_description:
            response = BaseResponse.error(
                message="AI system is currently unavailable",
                errors="Maaf, sistem AI sedang tidak tersedia. Silakan coba lagi nanti."
            )
            return jsonify(response.model_dump(exclude_none=True)), 500

        # Build response data
        response_data = SubmitAnswersData(
            session_id=manager.session_id,
            profile_description=profile_description,
            selected_package=manager.context["selected_package"],
            current_phase=manager.context["current_phase"]
        )
            
        # Wrap in BaseResponse
        response = BaseResponse[SubmitAnswersData].success(
            data=response_data,
            message="Answers submitted successfully"
        )
            
        return jsonify(response.model_dump(exclude_none=True))

    except Exception as e:
        response = BaseResponse.error(
            message="Failed to submit answers",
            errors=str(e)
        )
        return jsonify(response.model_dump(exclude_none=True)), 500