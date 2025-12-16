from flask import Blueprint, request, jsonify
import logging

from shared.session_manager import get_or_create_session
from shared.async_utils import run_async
from ..base.base_schemas import BaseResponse
from .usecases import generate_timeline
from . import timeline_v2

logger = logging.getLogger(__name__)

@timeline_v2.route('/questions', methods=['GET'])
def get_timeline_questions():
    """Get timeline profiling questions"""
    try:
        questions = {
            "timeline_profiling_questions": [
                {
                    "id": "target_level",
                    "question": "Ke level berapa Anda ingin meningkatkan kematangan Digital Forensics Readiness organisasi?",
                    "choices": [
                        {"label": "Level 2 - Managed"},
                        {"label": "Level 3 - Defined"},
                        {"label": "Level 4 - Quantitatively Managed"},
                        {"label": "Level 5 - Optimized"}
                    ]
                },
                {
                    "id": "timeline_duration",
                    "question": "Berapa lama target waktu yang Anda rencanakan untuk mencapai level tersebut?",
                    "choices": [
                        {"label": "3-6 bulan"},
                        {"label": "6-12 bulan"},
                        {"label": "1-2 tahun"},
                        {"label": "2+ tahun"}
                    ]
                },
                {
                    "id": "budget_allocation",
                    "question": "Berapa estimasi budget yang dapat dialokasikan untuk inisiatif DFR?",
                    "choices": [
                        {"label": "< 50 juta"},
                        {"label": "50-200 juta"},
                        {"label": "200-500 juta"},
                        {"label": "500+ juta"}
                    ]
                },
                {
                    "id": "dedicated_team",
                    "question": "Apakah organisasi memiliki atau berencana membentuk tim khusus untuk Digital Forensics?",
                    "choices": [
                        {"label": "Belum ada rencana"},
                        {"label": "Berencana membentuk (1-2 orang)"},
                        {"label": "Berencana membentuk (3-5 orang)"},
                        {"label": "Sudah ada tim (>5 orang)"}
                    ]
                },
                {
                    "id": "priority_enabler",
                    "question": "Enabler mana yang ingin diprioritaskan untuk peningkatan pertama?",
                    "choices": [
                        {"label": "1. Principles, Policies, and Frameworks"},
                        {"label": "2. Processes"},
                        {"label": "3. Organizational Structures"},
                        {"label": "4. Information"},
                        {"label": "5. Culture, Ethics, and Behavior"},
                        {"label": "6. People, Skills, and Competences"},
                        {"label": "7. Services, Infrastructure, and Applications"}
                    ]
                },
                {
                    "id": "management_commitment",
                    "question": "Seberapa besar dukungan dan komitmen manajemen untuk inisiatif DFR?",
                    "choices": [
                        {"label": "Minimal - belum menjadi prioritas"},
                        {"label": "Moderate - mendukung dengan keterbatasan"},
                        {"label": "Strong - prioritas menengah dengan budget memadai"},
                        {"label": "Full - prioritas tinggi dengan dukungan penuh"}
                    ]
                }
            ]
        }
        
        return jsonify(
            BaseResponse.success(
                data=questions,
                message="Timeline questions retrieved successfully"
            ).model_dump()
        ), 200
        
    except Exception as e:
        logger.error(f"Error getting timeline questions: {e}", exc_info=True)
        return jsonify(
            BaseResponse.error(
                message="Failed to get timeline questions",
                errors=str(e)
            ).model_dump()
        ), 500


@timeline_v2.route('/get_timeline_result', methods=['POST'])
def create_timeline():
    """Generate implementation timeline based on profiling answers"""
    try:
        manager = get_or_create_session()
        
        # Validate that assessment has been completed
        if not manager.context.get('score_enablers'):
            return jsonify(
                BaseResponse.error(
                    message="Please complete assessment first",
                    errors="No assessment results found"
                ).model_dump()
            ), 400
        
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify(
                BaseResponse.error(
                    message="Invalid request",
                    errors="Request body is required"
                ).model_dump()
            ), 400
        
        # Generate timeline
        logger.info("Generating timeline...")
        result = run_async(generate_timeline(manager, data))
        
        return jsonify(
            BaseResponse.success(
                data=result,
                message="Timeline generated successfully"
            ).model_dump()
        ), 200
        
    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        return jsonify(
            BaseResponse.error(
                message="Validation failed",
                errors=str(e)
            ).model_dump()
        ), 400
        
    except Exception as e:
        logger.error(f"Error generating timeline: {e}", exc_info=True)
        return jsonify(
            BaseResponse.error(
                message="Failed to generate timeline",
                errors=str(e)
            ).model_dump()
        ), 500