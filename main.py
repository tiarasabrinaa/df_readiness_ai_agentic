from flask import Flask, request, jsonify, session
from flask_cors import CORS
import uuid
import json
import asyncio
import random
from datetime import datetime
from typing import Dict, Any, List
from functools import wraps

# Local imports
from services.database_service import db_service
from services.llm_service import llm_service
from prompts import AssessmentPrompts

app = Flask(__name__)
app.secret_key = 'secret_key'
CORS(app, supports_credentials=True)

# Constants
PROFILING_QUESTIONS = [
    "Apa jenis industri atau bidang usaha yang Anda geluti?",
    "Berapa jumlah total karyawan di organisasi Anda?",
    "Apa posisi atau jabatan Anda dalam organisasi?",
    "Berapa tahun pengalaman Anda dalam bidang keamanan siber?",
    "Apakah organisasi Anda pernah mengalami insiden keamanan? Jika ya, jelaskan.",
    "Apakah Anda memiliki tim internal khusus untuk keamanan TI?",
    "Apakah organisasi Anda telah menjalani audit keamanan dalam 12 bulan terakhir?",
    "Jenis data sensitif apa yang Anda kelola (misalnya data pelanggan, keuangan, kesehatan)?",
    "Apakah Anda menggunakan solusi keamanan berbasis cloud atau on-premise?",
    "Seberapa sering dilakukan pelatihan atau sosialisasi keamanan kepada staf?"
]

QUESTION_KEYS = [
    "industry", "company_size", "position", "experience", "security_incidents",
    "has_security_team", "recent_audit", "sensitive_data", "security_solution", "training_frequency"
]

# Decorators
def async_route(f):
    """Decorator to handle async routes in Flask"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(f(*args, **kwargs))
        finally:
            loop.close()
    return wrapper

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
            "final_evaluation": {}
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
            "assessment_level": self.context["assessment_level"]
        }

# Global session storage
session_managers = {}

def get_or_create_session():
    """Get or create session manager"""
    session_id = session.get('session_id')
    
    if not session_id:
        session_id = request.headers.get('X-Session-ID')
        if not session_id and request.is_json:
            data = request.get_json()
            session_id = data.get('session_id') if data else None
    
    if not session_id or session_id not in session_managers:
        manager = SessionManager()
        session['session_id'] = manager.session_id
        session_managers[manager.session_id] = manager
        return manager
    
    if session_id != session.get('session_id'):
        session['session_id'] = session_id
    
    return session_managers[session_id]

# Database initialization
def startup():
    """Connect to database on startup"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def _startup():
        try:
            await db_service.connect()
            print("Database connected successfully")
            
            # Menghitung jumlah total pertanyaan di database
            question_count = await db_service.count_questions()
            print(f"Total questions in database: {question_count}")
            
            if question_count == 0:
                print("No questions found in database. You may need to load questions.")
        
        except Exception as e:
            print(f"Failed to initialize database: {str(e)}")
    
    try:
        loop.run_until_complete(_startup())
    finally:
        loop.close()


# Utility functions
def parse_answers_from_request(data: Dict) -> Dict[str, Any]:
    """Parse answers from request data in multiple formats"""
    qa_pairs = {}
    
    if 'answers' in data and isinstance(data['answers'], list):
        answers = data.get('answers', [])
        if len(answers) != len(PROFILING_QUESTIONS):
            raise ValueError(f"Please provide exactly {len(PROFILING_QUESTIONS)} answers.")
        
        for idx, answer in enumerate(answers):
            qa_pairs[f"question{idx+1}"] = answer
    
    elif any(key.startswith('question') for key in data.keys()):
        qa_pairs = {k: v for k, v in data.items() if k.startswith('question')}
        if len(qa_pairs) != len(PROFILING_QUESTIONS):
            raise ValueError(f"Please provide exactly {len(PROFILING_QUESTIONS)} question-answer pairs.")
    else:
        raise ValueError("Invalid format. Provide either an 'answers' array or 'question1'–'question10' keys.")
    
    return qa_pairs

def update_profile_from_qa(manager: SessionManager, qa_pairs: Dict[str, Any]):
    """Update user profile from Q&A pairs"""
    for idx, (question, answer) in enumerate(sorted(qa_pairs.items())):
        if idx < len(QUESTION_KEYS):
            manager.update_profile_data(QUESTION_KEYS[idx], answer)

async def get_assessment_level_from_llm(qa_pairs: Dict[str, Any]) -> tuple:
    """Get assessment level from LLM analysis"""
    # Generate the prompt for LLM
    prompt = AssessmentPrompts.get_profiling_analysis_prompt(qa_pairs)
    
    # Get the response from LLM service
    ai_response = await llm_service.generate_response(prompt, [])
    
    try:
        # Try parsing the response as JSON
        if '{' in ai_response and '}' in ai_response:
            json_start = ai_response.find('{')
            json_end = ai_response.rfind('}') + 1
            json_str = ai_response[json_start:json_end]
            llm_result = json.loads(json_str)
        else:
            raise json.JSONDecodeError("No JSON found", ai_response, 0)
        
        # Directly get the assessment level from the LLM response
        assessment_level = llm_result.get("assessment_level", "Recognize")
        
    except json.JSONDecodeError as e:

        print(f"JSON parsing failed: {str(e)}")
        print(f"Raw LLM response: {ai_response}")
        
        # Default result in case of failure
        llm_result = {
            "assessment_level": "Recognize",
        }
    
    # Return the assessment level and the LLM result
    return assessment_level, llm_result

async def get_questions_from_database(assessment_level: str) -> List[Dict]:
    """Get questions from database for the specified assessment level"""
    
    try:
        await db_service.disconnect()
        await db_service.connect()
        print("Database reconnected successfully")
    except Exception as e:
        print(f"Reconnection failed: {str(e)}")
        raise Exception(f"Database connection failed: {str(e)}")
    
    # Get questions for the specified level
    questions = await db_service.get_questions_by_level(assessment_level)
    
    if not questions:
        raise Exception(f"No questions found for the {assessment_level} level")
    
    return questions

async def evaluate_with_llm(manager: SessionManager) -> Dict[str, Any]:
    """Perform comprehensive evaluation using LLM"""
    questions = manager.context["test_questions"]
    answers = manager.context["test_answers"]
    user_profile = manager.context["user_profile"]
    assessment_level = manager.context["assessment_level"]
    qa_pairs = manager.context.get("profiling_qa_pairs", {})
    
    prompt = AssessmentPrompts.get_evaluation_prompt(
        user_profile, assessment_level, qa_pairs, questions, answers
    )
    
    ai_response = await llm_service.generate_response(prompt, [])
    
    try:
        if '{' in ai_response and '}' in ai_response:
            json_start = ai_response.find('{')
            json_end = ai_response.rfind('}') + 1
            json_str = ai_response[json_start:json_end]
            evaluation = json.loads(json_str)
        else:
            raise json.JSONDecodeError("No JSON found", ai_response, 0)
            
    except json.JSONDecodeError as e:
        print(f"Evaluation JSON parsing failed: {str(e)}")
        evaluation = AssessmentPrompts.get_fallback_evaluation()
        evaluation["raw_llm_response"] = ai_response
    
    return evaluation

# Routes
@app.route('/', methods=['GET'])
def home():
    """API information"""
    return jsonify({
        "message": "ok"
    })

@app.route('/start_profiling', methods=['GET'])
def start_profiling():
    """Return profiling questions for cybersecurity assessment"""
    try:
        manager = get_or_create_session()
        
        return jsonify({
            "session_id": manager.session_id,
            "questions": PROFILING_QUESTIONS,
            "total_questions": len(PROFILING_QUESTIONS),
            "current_phase": manager.context.get("current_phase", "profiling"),
        })
        
    except Exception as e:
        print(f"Error in start_profiling: {str(e)}")
        return jsonify({"error": str(e)}), 500
    
@app.route('/submit_answers', methods=['POST'])
@async_route
async def submit_answers():
    """Process profiling answers and determine assessment level using LLM"""
    try:
        manager = get_or_create_session()
        
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
        
        data = request.get_json()
        
        try:
            qa_pairs = parse_answers_from_request(data)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        
        update_profile_from_qa(manager, qa_pairs)
        
        # Get the assessment level from LLM
        assessment_level, llm_result = await get_assessment_level_from_llm(qa_pairs)
        
        # Store the assessment level in the session
        manager.context["assessment_level"] = assessment_level
        manager.context["current_phase"] = "assessment_level"
        manager.context["llm_analysis"] = llm_result
        manager.context["profiling_qa_pairs"] = qa_pairs
        
        return jsonify({
            "session_id": manager.session_id,
            "assessment_level": assessment_level,
            "current_phase": manager.context["current_phase"],
        })
        
    except Exception as e:
        print(f"Error in submit_answers: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/get_test_questions', methods=['GET'])
@async_route
async def get_test_questions():
    """Get questions from MongoDB based on assessment level"""
    try:
        manager = get_or_create_session()
        
        if manager.context["current_phase"] != "assessment_level":
            return jsonify({"error": "Please complete profiling first"}), 400
        
        assessment_level = manager.context.get("assessment_level")
        if not assessment_level:
            return jsonify({"error": "Assessment level not determined. Please complete profiling first."}), 400
        
        print(f"Fetching questions from MongoDB for level: {assessment_level}")
        
        try:
            questions = await get_questions_from_database(assessment_level)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        
        if not questions:
            return jsonify({"error": f"No questions found for {assessment_level} level."}), 404
        
        manager.context["test_questions"] = questions
        manager.context["current_phase"] = "testing"
        
        return jsonify({
            "session_id": manager.session_id,
            "assessment_level": assessment_level,
            "questions": questions,
            "current_phase": manager.context["current_phase"],
        })
        
    except Exception as e:
        print(f"Error getting test questions: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/submit_test_answers', methods=['POST'])
def submit_test_answers():
    """Submit test answers and prepare for LLM evaluation"""
    try:
        manager = get_or_create_session()
        
        if manager.context["current_phase"] != "testing":
            return jsonify({"error": "Please get test questions first"}), 400
        
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
        
        data = request.get_json()
        answers = data.get('answers', [])
        
        expected_count = len(manager.context["test_questions"])
        if len(answers) != expected_count:
            return jsonify({"error": f"Please provide exactly {expected_count} answers"}), 400
        
        # Validate answers
        if not all(str(answer).strip() for answer in answers):
            return jsonify({"error": "All answers must be non-empty"}), 400
        
        # Store answers
        manager.context["test_answers"] = answers
        manager.context["current_phase"] = "evaluation"
        
        return jsonify({
            "session_id": manager.session_id, 
            "current_phase": manager.context["current_phase"],
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get_results', methods=['GET'])
@async_route
async def get_results():
    """Get final evaluation and recommendations using LLM"""
    try:
        manager = get_or_create_session()
        
        if manager.context["current_phase"] != "evaluation":
            return jsonify({"error": "Please submit test answers first"}), 400
        
        # Perform LLM evaluation
        evaluation = await evaluate_with_llm(manager)
        
        # Store final evaluation
        manager.context["final_evaluation"] = evaluation
        manager.context["current_phase"] = "completed"
        
        return jsonify({
            "session_id": manager.session_id,
            "assessment_level": manager.context["assessment_level"],
            "user_profile": manager.context["user_profile"],
            "profiling_qa": manager.context.get("profiling_qa_pairs", {}),
            "test_questions": len(manager.context["test_questions"]),
            "evaluation": evaluation,
            "questions_answered": len(manager.context["test_answers"]),
            "current_phase": manager.context["current_phase"],
            "assessment_complete": True,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"Error in get_results: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/session_status', methods=['GET'])
def session_status():
    """Get current session status"""
    try:
        manager = get_or_create_session()
        return jsonify({
            "session_id": manager.session_id,
            "current_phase": manager.context["current_phase"],
            "assessment_level": manager.context.get("assessment_level"),
            "profiling_progress": f"{manager.context['profiling_progress']}/{manager.context['total_profiling_questions']}",
            "created_at": manager.created_at.isoformat(),
            "questions_available": len(manager.context.get("test_questions", [])),
            "answers_submitted": len(manager.context.get("test_answers", []))
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        "error": "Method not allowed",
        "message": "Please check the HTTP method (GET/POST) for this endpoint"
    }), 405

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    # Initialize database connection
    try:
        startup()
    except Exception as e:
        print(f"Startup failed: {str(e)}")
    
    app.run(debug=True, host='0.0.0.0', port=5001)