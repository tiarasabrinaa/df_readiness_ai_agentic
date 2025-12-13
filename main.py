from flask import Flask, request, jsonify, session
import os
from flask_cors import CORS
import uuid
import json
import asyncio
import random
import numpy as np
import faiss
from datetime import datetime
from typing import Dict, Any, List
from functools import wraps
import resend
import threading
from sentence_transformers import SentenceTransformer
from pymongo import MongoClient
# Local imports
from services.database_service import db_service
from api.auth.models import db as pg_db, User
from api.auth import auth_bp
from api.auth.jwt_utils import decode_token
from services.llm_service import llm_service
from prompts import AssessmentPrompts
from config.settings import settings
from email_template import generate_email_template



app = Flask(__name__)

# registering blueprints
from api.auth import auth_bp as auth_bp
from api.start_profiling import start_profiling_bp as start_profiling_bp
from api.assessment_before import assessment_before_bp as assessment_before_bp
from api.result import result as result_bp
from api.rag_faiss import rag_faiss_bp

from api.v2.assessment_before import assessment_before_bp as assessment_before_bp_v2

app.secret_key = 'secret_key'
CORS(app, supports_credentials=True)

# SQLAlchemy (PostgreSQL) configuration
app.config['SQLALCHEMY_DATABASE_URI'] = settings.POSTGRES_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
pg_db.init_app(app)

app.register_blueprint(auth_bp, url_prefix='/api/v1/auth')
app.register_blueprint(start_profiling_bp, url_prefix='/api/v1/start_profiling')
app.register_blueprint(assessment_before_bp, url_prefix='/api/v1/assessment_before')
app.register_blueprint(result_bp, url_prefix='/api/v1/result')
app.register_blueprint(rag_faiss_bp, url_prefix='/api/v1/rag_faiss')
app.register_blueprint(assessment_before_bp_v2, url_prefix='/api/v2/assessment_before')

@app.before_request
def jwt_protect_routes():
    # Allow public endpoints
    public_paths = {'/', '/api/v1/auth/login', '/api/v1/auth/register', '/api/v1/auth/refresh'}
    if request.path in public_paths or request.path.startswith('/static'):
        return
    # Skip OPTIONS for CORS preflight
    if request.method == 'OPTIONS':
        return
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.lower().startswith('bearer '):
        return jsonify({'error': 'authorization header missing'}), 401
    token = auth_header.split(' ', 1)[1].strip()
    try:
        payload = decode_token(token)
        if payload.get('type') != 'access':
            return jsonify({'error': 'invalid token type'}), 401
        user = User.query.get(payload.get('sub'))
        if not user:
            return jsonify({'error': 'user not found'}), 401
        # Attach user to request
        setattr(request, 'current_user', user)
    except Exception as e:
        return jsonify({'error': 'invalid token', 'detail': str(e)}), 401

# Global event loop for async operations


# Initialize sentence transformer model for embeddings
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# Global FAISS index
faiss_index = None
package_mappings = {}



# Add timeout configuration for different operations
TIMEOUTS = {
    'llm_evaluation': 300,  # 5 minutes for complex evaluations
    'database_query': 30,   # 30 seconds for database operations
    'faiss_search': 60,     # 1 minute for similarity search
    'default': 120          # 2 minutes default
}

# Database initialization
async def startup_async():
    """Async startup function"""
    try:
        await db_service.connect()
        print("Database connected successfully")
        
        question_count = await db_service.count_questions()
        keterangan_count = await db_service.count_keterangan()
        
        print(f"Total questions in database: {question_count}")
        print(f"Total keterangan in database: {keterangan_count}")
        
        if question_count == 0:
            print("No questions found in database. You may need to load questions.")
        
        if keterangan_count == 0:
            print("No keterangan found in database. You may need to load keterangan data.")
        
        # Initialize FAISS index
        if keterangan_count > 0:
            await initialize_faiss_index()
    
    except Exception as e:
        print(f"Failed to initialize database: {str(e)}")

def startup():
    """Connect to database on startup using persistent event loop"""
    loop = get_event_loop()
    future = asyncio.run_coroutine_threadsafe(startup_async(), loop)
    future.result(timeout=15)  # 15 second timeout for startup

# Routes
@app.route('/', methods=['GET'])
def home():
    """API information"""
    return jsonify({
        "message": "Digital Forensics Readiness Assessment API",
        "version": "2.0",
        "features": ["Profiling", "FAISS Similarity Search", "Likert Scale Assessment", "LLM Evaluation"]
    })

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

@app.route('/check_db', methods=['GET'])
def check_db():
    try:
        client = MongoClient('mongodb://admin:securepassword123@mongodb:27017/cybersecurity_assessment?authSource=admin')
        db = client.cybersecurity_assessment
        keterangan_count = db.keterangan.count_documents({})
        questions_count = db.question_before_v1.count_documents({})
        return jsonify({
            "keterangan_count": keterangan_count,
            "questions_count": questions_count
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def parse_timeline_answers(data: Dict) -> Dict[str, Any]:
    """Parse timeline profiling answers from request"""
    timeline_answers = {}
    
    if 'answers' in data and isinstance(data['answers'], list):
        answers = data.get('answers', [])
        if len(answers) != len(TIMELINE_PROFILING_QUESTIONS):
            raise ValueError(f"Please provide exactly {len(TIMELINE_PROFILING_QUESTIONS)} answers.")
        
        for idx, answer in enumerate(answers):
            timeline_answers[TIMELINE_QUESTION_KEYS[idx]] = answer
    
    elif any(key in TIMELINE_QUESTION_KEYS for key in data.keys()):
        for key in TIMELINE_QUESTION_KEYS:
            if key in data:
                timeline_answers[key] = data[key]
        
        if len(timeline_answers) != len(TIMELINE_PROFILING_QUESTIONS):
            raise ValueError(f"Please provide all {len(TIMELINE_PROFILING_QUESTIONS)} answers.")
    
    else:
        raise ValueError("Invalid format. Provide either 'answers' array or individual answer keys.")
    
    return timeline_answers

@app.route('/get_timeline', methods=['POST'])
@async_route
async def get_timeline():
    """Generate simple timeline roadmap based on profiling answers"""
    try:
        manager = get_or_create_session()
        
        # Validate phase
        # if manager.context.get("current_phase") != "timeline_profiling":
        #     return jsonify({
        #         "error": "Please start timeline profiling first using /start_profiling_timeline"
        #     }), 400
        
        # Validate request
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
        
        data = request.get_json()
        timeline_answers = data.get('answers', [])
        
        if len(timeline_answers) != len(TIMELINE_PROFILING_QUESTIONS):
            return jsonify({
                "error": f"Please provide exactly {len(TIMELINE_PROFILING_QUESTIONS)} answers"
            }), 400
        
        # Store timeline profiling data
        manager.context["timeline_profiling_data"] = timeline_answers
        
        # Get assessment data
        final_evaluation = manager.context.get("final_evaluation", {})
        if isinstance(final_evaluation, str):
            try:
                final_evaluation = json.loads(final_evaluation)
            except (json.JSONDecodeError, ValueError):
                final_evaluation = {}
        
        # Get current level from assessment
        current_level_str = final_evaluation.get("current_level", "Level 0")
        # Extract number from "Level X"
        try:
            current_level = int(current_level_str.split()[-1])
        except:
            current_level = 0
        
        avg_score = manager.context.get("likert_scores", [])
        avg_score = calculate_likert_average(avg_score) if avg_score else 0.0
        
        # Parse target level and duration from answers
        duration_answer = timeline_answers[0]  # First question is about duration
        if "3-6" in duration_answer:
            target_months = 6
        elif "6-12" in duration_answer:
            target_months = 12
        elif "12-18" in duration_answer:
            target_months = 18
        elif "18-24" in duration_answer:
            target_months = 24
        else:
            target_months = 12
        
        if target_months <= 6:
            target_level = min(current_level + 1, 5)
        elif target_months <= 12:
            target_level = min(current_level + 2, 5)
        elif target_months <= 18:
            target_level = min(current_level + 3, 5)
        else:
            target_level = min(current_level + 4, 5)
        
        # Build context for LLM
        priority = timeline_answers[1] if len(timeline_answers) > 1 else "Semua aspek"
        budget = timeline_answers[2] if len(timeline_answers) > 2 else "100-500 juta"
        team_size = timeline_answers[3] if len(timeline_answers) > 3 else "Ada, 3-10 orang"
        
        # Calculate start date (today)
        from datetime import datetime, timedelta
        start_date = datetime.now()
        
        # Simple prompt for timeline generation
        timeline_prompt = f"""
Buatkan roadmap Digital Forensic Readiness (DFR) yang SANGAT SIMPEL.

KONDISI:
- Level sekarang: Level {current_level}
- Target level: Level {target_level}
- Durasi: {target_months} bulan
- Prioritas: {priority}

INSTRUKSI:
Buat {target_months * 2} action items (2 per bulan) dengan format STRICT berikut.
Mulai dari tanggal {start_date.strftime('%Y-%m-%d')}.

RETURN HANYA JSON INI (NO MARKDOWN, NO BACKTICKS):
{{
  "current_level": {current_level},
  "target_level": {target_level},
  "timeline": [
    {{"date": "2025-10-14", "action": "Lakukan assessment DFR capability saat ini", "priority": "High"}},
    {{"date": "2025-10-21", "action": "Identifikasi gap antara current dan target level", "priority": "High"}},
    {{"date": "2025-10-28", "action": "Buat draft policy DFR", "priority": "Medium"}}
  ]
}}

Action harus:
- Spesifik dan jelas
- Realistis untuk team size {team_size}
- Sesuai prioritas {priority}
- Progress bertahap dari Level {current_level} ke {target_level}

RETURN ONLY JSON, NOTHING ELSE!
"""

        try:
            print("Generating simple timeline roadmap...")
            timeline_response = await llm_service.generate_response(timeline_prompt, [])
            
            # Clean response
            timeline_response = timeline_response.strip()
            
            # Remove markdown code blocks if present
            if timeline_response.startswith("```"):
                lines = timeline_response.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                timeline_response = "\n".join(lines).strip()
            
            # Parse JSON
            timeline_data = json.loads(timeline_response)
            
            # Validate structure
            if "timeline" not in timeline_data or not isinstance(timeline_data["timeline"], list):
                raise ValueError("Invalid timeline structure")
            
            # Store timeline data
            manager.context["timeline_data"] = timeline_data
            manager.context["current_phase"] = "timeline_generated"
            
            print(f"Successfully generated timeline with {len(timeline_data.get('timeline', []))} action items")
            
            return jsonify({
                "session_id": manager.session_id,
                "timeline_generated": True,
                "current_phase": manager.context["current_phase"],
                "current_level": current_level,
                "target_level": target_level,
                "duration_months": target_months,
                "actions": timeline_data.get('timeline', []),
                "total_actions": len(timeline_data.get('timeline', [])),
                "generated_at": datetime.now().isoformat()
            })
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {str(e)}")
            print(f"Response preview: {timeline_response[:300]}")
            
            return jsonify({
                "error": "Failed to parse timeline response",
                "error_details": str(e),
                "raw_preview": timeline_response[:300]
            }), 500
            
    except Exception as e:
        print(f"Error in get_timeline: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Initialize database connection
    try:
        startup()
    except Exception as e:
        print(f"Startup failed: {str(e)}")
    # Create Postgres tables
    with app.app_context():
        try:
            pg_db.create_all()
            print("PostgreSQL tables ensured.")
            # Seed default user if not exists
            try:
                from api.auth.models import User as SeedUser
                if not SeedUser.query.filter((SeedUser.username=="kingrokade") | (SeedUser.email=="kingrokade")).first():
                    u = SeedUser(username="kingrokade", email="kingrokade@example.com")
                    u.set_password("benteng88")
                    pg_db.session.add(u)
                    pg_db.session.commit()
                    print("Seeded default user: kingrokade / benteng88")
                else:
                    print("Default user already present.")
            except Exception as se:
                print(f"Seeding default user failed: {se}")
        except Exception as e:
            print(f"Failed to create PostgreSQL tables: {e}")

    app.run(debug=True, host='0.0.0.0', port=5001)