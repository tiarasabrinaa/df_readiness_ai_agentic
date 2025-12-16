from typing import Dict, Any
from datetime import datetime, date
import logging
import json

from shared.session_manager import SessionManager
from services.llm_service import llm_service
from .prompts import build_timeline_messages
from .utils import (
    parse_timeline_answers,
    parse_timeline_json,
    format_timeline_response
)

logger = logging.getLogger(__name__)


async def generate_timeline(
    manager: SessionManager,
    data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate implementation timeline based on assessment results and profiling
    
    Args:
        manager: SessionManager with assessment context
        data: Request data with timeline profiling answers
        
    Returns:
        Dict containing generated timeline
        
    Raises:
        ValueError: If validation fails or data is invalid
    """
    try:
        # Parse timeline answers
        timeline_answers = parse_timeline_answers(data)
        logger.info(f"Timeline answers: {timeline_answers}")
        
        # Get data from manager context
        profile_description = manager.context.get('profile_description', '')
        score_enablers = manager.context.get('score_enablers', {})
        highest_enabler = manager.context.get('highest_enabler', {"name": "N/A", "score": 0})
        lowest_enabler = manager.context.get('lowest_enabler', {"name": "N/A", "score": 0})
        maturity_level = manager.context.get('maturity_level', 1)

        time = date.today()
        
        # Build LLM messages
        timeline_messages = build_timeline_messages(
            time=time,
            profile_description=profile_description,
            current_level=maturity_level,
            lowest_enabler=lowest_enabler,
            highest_enabler=highest_enabler,
            score_enablers=score_enablers,
            timeline_answers=timeline_answers,
            questions_answers=manager.context.get('question_answers', {})
        )
        
        # Generate timeline with LLM
        logger.info("Generating timeline with LLM...")
        timeline_response = await llm_service.call_llm(timeline_messages, max_tokens=3000, temperature=0.7)
        
        # Parse timeline JSON
        timeline = parse_timeline_json(timeline_response)
        logger.info("Timeline generated successfully")
        
        # Store timeline in context
        manager.context['timeline'] = timeline
        manager.context['timeline_answers'] = timeline_answers
        
        # Format response
        formatted_timeline = format_timeline_response(timeline)
        
        return {
            "timeline": formatted_timeline
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {e}")
        raise ValueError(f"Failed to parse timeline: Invalid JSON format")
    except Exception as e:
        logger.error(f"Error generating timeline: {e}", exc_info=True)
        raise