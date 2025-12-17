from typing import Dict, Any, List
import json
import re
from shared.session_manager import SessionManager

def clean_json_response(llm_response: str) -> str:
    """
    Clean LLM response to extract valid JSON
    
    Args:
        llm_response: Raw LLM response that might contain markdown or extra text
        
    Returns:
        Clean JSON string
    """
    # Remove markdown code blocks
    cleaned = re.sub(r'```json\s*', '', llm_response)
    cleaned = re.sub(r'```\s*', '', cleaned)
    
    # Find JSON object/array
    # Try to find { ... } or [ ... ]
    match = re.search(r'(\{.*\}|\[.*\])', cleaned, re.DOTALL)
    if match:
        cleaned = match.group(1)
    
    return cleaned.strip()

def parse_timeline_answers(data: Dict[str, Any]) -> Dict[str, str]:
    """
    Parse timeline profiling answers from request data
    
    Args:
        data: Request data containing answers array
        
    Returns:
        Dict with answer keys mapped to values
    """
    answers = data.get('answers', [])
    
    expected_keys = [
        'target_level',
        'timeline_duration', 
        'budget_allocation',
        'dedicated_team',
        'priority_enabler',
        'management_commitment'
    ]
    
    if len(answers) != len(expected_keys):
        raise ValueError(f"Expected {len(expected_keys)} answers, got {len(answers)}")
    
    return dict(zip(expected_keys, answers))

def parse_timeline_json(llm_response: str) -> Dict[str, Any]:
    """
    Parse timeline JSON from LLM response
    
    Args:
        llm_response: Raw LLM response
        
    Returns:
        Parsed timeline dict
        
    Raises:
        ValueError: If JSON parsing fails
    """
    try:
        cleaned = clean_json_response(llm_response)
        timeline = json.loads(cleaned)
        
        # Validate required fields based on new structure
        required_fields = ['total_duration', 'timeline', 'risks']
        for field in required_fields:
            if field not in timeline:
                raise ValueError(f"Missing required field in timeline: {field}")
        
        # Validate timeline array structure
        if not isinstance(timeline['timeline'], list):
            raise ValueError("'timeline' must be an array")
        
        # Validate each timeline item has required fields
        for idx, item in enumerate(timeline['timeline']):
            required_item_fields = ['tanggal_mulai', 'tanggal_selesai', 'task', 'focus_enabler']
            for field in required_item_fields:
                if field not in item:
                    raise ValueError(f"Timeline item {idx} missing required field: {field}")
        
        # Validate risks array structure
        if not isinstance(timeline['risks'], list):
            raise ValueError("'risks' must be an array")
        
        for idx, risk in enumerate(timeline['risks']):
            if 'risk' not in risk or 'mitigation' not in risk:
                raise ValueError(f"Risk item {idx} missing 'risk' or 'mitigation' field")
        
        return timeline
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse timeline JSON: {e}")

def format_timeline_response(timeline: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format timeline for API response
    
    Args:
        timeline: Parsed timeline dict
        
    Returns:
        Formatted timeline dict
    """
    return {
        "total_duration": timeline.get('total_duration', ''),
        "timeline": timeline.get('timeline', []),
        "risks": timeline.get('risk_mitigation', timeline.get('risks', []))  # Support both field names
    }