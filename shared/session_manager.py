import asyncio
from flask import Flask, request, jsonify, session
from datetime import datetime
import uuid
import threading

from functools import wraps

from lib.profiling_question import PROFILING_QUESTIONS

_loop = None
_loop_thread = None

session_managers = {}

# Session Management
class SessionManager:
    """Session manager with LLM integration"""
    
    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.created_at = datetime.now()
        self.context = {
            "user_profile": {},
            "current_phase": "profiling",
            "profiling_data": {},
            "assessment_level": None,
            "profiling_progress": 0,
            "total_profiling_questions": len(PROFILING_QUESTIONS),
            "test_questions": [],
            "test_answers": [],
            "final_evaluation": {},
            "profile_description": "",
            "selected_package": "",
            "likert_scores": []
        }
        self.conversation_summary = ""
        self.last_ai_message = ""
    
    def update_profile_data(self, key: str, value: str):
        """Update specific profile data"""
        self.context["user_profile"][key] = value
    
    def get_context_for_llm(self) -> dict:
        """Get context for LLM processing"""
        return {
            "session_id": self.session_id,
            "phase": self.context["current_phase"],
            "user_profile": self.context["user_profile"],
            "profiling_progress": f"{self.context['profiling_progress']}/{self.context['total_profiling_questions']}",
            "assessment_level": self.context["assessment_level"],
            "selected_package": self.context["selected_package"]
        }

def get_or_create_session():
    """Get or create session manager"""
    session_id = (
        request.args.get('session_id') or
        request.headers.get('X-Session-ID') or
        ((request.get_json(silent=True) or {}).get('session_id') if request.is_json else None) or
        session.get('session_id')
    )
    
    if not session_id or session_id not in session_managers:
        manager = SessionManager()
        session['session_id'] = manager.session_id
        session_managers[manager.session_id] = manager
        return manager
    
    if session_id != session.get('session_id'):
        session['session_id'] = session_id
    
    return session_managers[session_id]

def async_route(f):
    """Decorator for async route handlers using main event loop"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        
        loop = get_event_loop()
        future = asyncio.run_coroutine_threadsafe(f(*args, **kwargs), loop)
        
        try:
            # 2 minutes timeout for LLM operations
            return future.result(timeout=120)
        except asyncio.TimeoutError:
            return jsonify({
                "error": "Request timeout", 
                "message": "The analysis is taking longer than expected. Please try again."
            }), 504
        except Exception as e:
            print(f"Async route error: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500
    
    return wrapper

def get_event_loop():
    """Get or create a persistent event loop for async operations"""
    global _loop, _loop_thread
    
    if _loop is None or _loop.is_closed():
        def run_loop():
            global _loop
            _loop = asyncio.new_event_loop()
            asyncio.set_event_loop(_loop)
            _loop.run_forever()
        
        _loop_thread = threading.Thread(target=run_loop, daemon=True)
        _loop_thread.start()
        
        # Wait for loop to be created
        while _loop is None:
            threading.Event().wait(0.01)
    
    return _loop