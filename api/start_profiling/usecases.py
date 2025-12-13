# api/profiling/usecases.py
from services.llm_service import LLMService
from typing import List, Dict, Any
import logging

from .prompts import build_profile_description_messages
from .utils import format_profile_text, parse_answers_from_request, update_profile_from_qa, update_manager_phase_profiling

logger = logging.getLogger("debug_logger")
llm_service = LLMService()

async def generate_profile_description(
    manager: Any,
    answer_submission: Dict[str, Any],
    questions: List[Dict]
) -> str:
    """
    Generate profile description from Q&A pairs using LLM
    
    Args:
        qa_pairs: Dictionary of user answers
        questions: List of profiling questions
        
    Returns:
        AI-generated profile description
    """
    try:

        qa_pairs = parse_answers_from_request(answer_submission)
        update_profile_from_qa(manager, qa_pairs)

        profile_text = format_profile_text(qa_pairs, questions)
        messages = build_profile_description_messages(profile_text)

        description = await llm_service.call_llm(messages)
        manager = update_manager_phase_profiling(manager, description, qa_pairs)
        
        return description.strip()
        
    except Exception as e:
        logger.error(f"Error generating profile description: {e}")
        logger.warning("Using fallback: returning formatted profile text")
        return profile_text
    
