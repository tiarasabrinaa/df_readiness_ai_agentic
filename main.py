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
app.secret_key = 'secret_key'
CORS(app, supports_credentials=True)

# SQLAlchemy (PostgreSQL) configuration
app.config['SQLALCHEMY_DATABASE_URI'] = settings.POSTGRES_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
pg_db.init_app(app)
app.register_blueprint(auth_bp, url_prefix='/auth')

@app.before_request
def jwt_protect_routes():
    # Allow public endpoints
    public_paths = {'/', '/auth/login', '/auth/register', '/auth/refresh'}
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
_loop = None
_loop_thread = None

# Initialize sentence transformer model for embeddings
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# Global FAISS index
faiss_index = None
package_mappings = {}

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

# Constants
PROFILING_QUESTIONS = [
  {
    "type": "organization",
    "question": "Apakah organisasi Anda tergolong dalam kategori Usaha Mikro, Kecil, dan Menengah (UMKM)?",
    "choices": [
      { "label": "Ya, organisasi saya termasuk UMKM" },
      { "label": "Tidak, organisasi saya bukan UMKM" }
    ]
  },
  {
    "type": "organization",
    "question": "Apakah organisasi Anda merupakan Badan Usaha Milik Negara (BUMN)?",
    "choices": [
      { "label": "Ya, organisasi saya adalah BUMN" },
      { "label": "Tidak, organisasi saya bukan BUMN" }
    ]
  },
  {
    "type": "organization",
    "question": "Berapa jumlah karyawan di organisasi Anda?",
    "choices": [
      { "label": "<10" },
      { "label": "10-50" },
      { "label": "51-200" },
      { "label": "200+"}
    ]
  },
  {
    "type": "organization",
    "question": "Berapa omzet tahunan organisasi Anda?",
    "choices": [
      { "label": "< 1 Miliar" },
      { "label": "1-5 Miliar" },
      { "label": "6-20 Miliar" },
      { "label": "20+ Miliar" }
    ]
  },
  {
    "type": "organization",
    "question": "Bagaimana status permodalan organisasi Anda?",
    "choices": [
      { "label": "Mandiri" },
      { "label": "Dibiayai oleh investor"},
      { "label": "Dibiayai oleh bank atau lembaga keuangan lainnya" }
    ]
  },
  {
    "type": "organization",
    "question": "Seperti apa struktur organisasi Anda?",
    "choices": [
      { "label": "Piramidal" },
      { "label": "Flat" },
      { "label": "Matriks" },
      { "label": "Lainnya", "is_field": True }
    ]
  },
  {
    "type": "organization",
    "question": "Berapa total asset yang dimiliki oleh organisasi Anda?",
    "choices": [
      { "label": "< 1 Miliar" },
      { "label": "1 - 10 Miliar" },
      { "label": "11 - 50 Miliar"},
      { "label": "50+ Miliar"}
    ]
  },
  {
    "type": "organization",
    "question": "Berapa besar pajak yang dibayarkan oleh organisasi Anda dalam setahun?",
    "choices": [
      { "label": "<500 Juta" },
      { "label": "500 Juta - 5 Miliar" },
      { "label": "5 - 50 Miliar" },
      { "label": "50+ Miliar" }
    ]
  },
  {
    "type": "personal",
    "question": "Berapa lama Anda telah menjabat posisi ini?",
    "choices": [
      { "label": "< 1 tahun" },
      { "label": "1-3 tahun" },
      { "label": "4-5 tahun" },
      { "label": "> 5 tahun"}
    ]
  },
  {
    "type": "personal",
    "question": "Apa tingkat pendidikan Anda?",
    "choices": [
      { "label": "SMA/SMK" },
      { "label": "D3" },
      { "label": "S1" },
      { "label": "S2" },
      { "label": "S3" },
      { "label": "Lainnya", "is_field": True }
    ]
  },
  {
    "type": "personal",
    "question": "Apa pengalaman kerja Anda dalam bidang ini?",
    "choices": [
      { "label": "< 1 tahun" },
      { "label": "1-3 tahun" },
      { "label": "4-5 tahun" },
      { "label": "> 5 tahun" },
      { "label": "Lainnya", "is_field": True }
    ]
  }
]

QUESTION_KEYS = [
    "umkm", "bumn", "company_size", "omzet", "funding", "structure", "total_assets", "tax", "tenure", "education", "experience"
]

# Decorators
# Updated async_route decorator with longer timeout
def async_route(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        loop = get_event_loop()
        future = asyncio.run_coroutine_threadsafe(f(*args, **kwargs), loop)
        try:
            # Increase timeout for LLM operations
            return future.result(timeout=120)  # 2 minutes instead of 60 seconds
        except asyncio.TimeoutError:
            return jsonify({
                "error": "Request timeout", 
                "message": "The analysis is taking longer than expected. Please try again."
            }), 504
        except Exception as e:
            print(f"Async route error: {str(e)}")
            return jsonify({"error": str(e)}), 500
    return wrapper

# Add timeout configuration for different operations
TIMEOUTS = {
    'llm_evaluation': 300,  # 5 minutes for complex evaluations
    'database_query': 30,   # 30 seconds for database operations
    'faiss_search': 60,     # 1 minute for similarity search
    'default': 120          # 2 minutes default
}

# FAISS and Embedding Functions
async def generate_profile_description(qa_pairs: Dict[str, Any]) -> str:
    """Generate profile description using LLM based on Q&A pairs"""
    
    # Create a structured prompt for LLM
    profile_info = []
    for i, (key, answer) in enumerate(qa_pairs.items()):
        question = PROFILING_QUESTIONS[i]["question"]
        profile_info.append(f"Q: {question}\nA: {answer}")
    
    profile_text = "\n\n".join(profile_info)
    
    prompt = f"""
    Berdasarkan informasi profiling pengguna berikut, buatlah deskripsi karakteristik organisasi dan pengguna dalam 1 paragraf yang komprehensif:

    {profile_text}

    Buatlah deskripsi yang mencakup:
    - Karakteristik organisasi (ukuran, jenis, struktur)
    - Profil pengguna (pengalaman, pendidikan, posisi)
    - Konteks bisnis dan operasional

    Deskripsi harus dalam bahasa Indonesia dan dapat digunakan untuk menentukan paket assessment yang paling sesuai.
    """
    
    try:
        description = await llm_service.generate_response(prompt, [])
        return description.strip()
    except Exception as e:
        print(f"Error generating profile description: {str(e)}")
        return f"Organisasi dengan {qa_pairs.get('question3', 'ukuran tidak diketahui')} karyawan dan struktur {qa_pairs.get('question6', 'tidak diketahui')}"

def create_embedding(text: str) -> np.ndarray:
    """Create embedding vector for given text"""
    try:
        embedding = embedding_model.encode([text])
        return embedding[0]
    except Exception as e:
        print(f"Error creating embedding: {str(e)}")
        # Return zero vector as fallback
        return np.zeros(384)  # all-MiniLM-L6-v2 has 384 dimensions

async def initialize_faiss_index():
    """Initialize FAISS index from database keterangan collection"""
    global faiss_index, package_mappings
    
    try:
        # Get all descriptions from keterangan collection
        await db_service.connect()
        keterangan_docs = await db_service.get_all_keterangan()
        
        if not keterangan_docs:
            print("No keterangan documents found in database")
            return False
        
        print(f"Found {len(keterangan_docs)} keterangan documents")
        
        # Create embeddings for all descriptions
        descriptions = []
        packages = []
        
        for doc in keterangan_docs:
            description = doc.get('description', '')
            package = doc.get('package', doc.get('paket', 'unknown'))
            
            if description and package:
                descriptions.append(description)
                packages.append(package)
        
        if not descriptions:
            print("No valid descriptions found")
            return False
        
        print(f"Creating embeddings for {len(descriptions)} descriptions...")
        embeddings = []
        for desc in descriptions:
            embedding = create_embedding(desc)
            embeddings.append(embedding)
        
        embeddings_array = np.array(embeddings).astype('float32')
        
        # Create FAISS index
        dimension = embeddings_array.shape[1]
        faiss_index = faiss.IndexFlatIP(dimension)  # Inner product for similarity
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings_array)
        faiss_index.add(embeddings_array)
        
        # Create package mappings
        package_mappings = {i: packages[i] for i in range(len(packages))}
        
        print(f"FAISS index initialized with {faiss_index.ntotal} vectors")
        return True
        
    except Exception as e:
        print(f"Error initializing FAISS index: {str(e)}")
        return False

async def find_best_package(profile_description: str) -> str:
    """Find best matching package using FAISS similarity search"""
    global faiss_index, package_mappings
    
    if faiss_index is None:
        print("FAISS index not initialized, initializing now...")
        await initialize_faiss_index()
    
    if faiss_index is None:
        print("Failed to initialize FAISS index, returning default package '0'")
        return '0'  # Return '0' as the default package
    
    try:
        # Create embedding for profile description
        query_embedding = create_embedding(profile_description)
        query_embedding = np.array([query_embedding]).astype('float32')
        
        # Normalize for cosine similarity
        faiss.normalize_L2(query_embedding)
        
        # Search for the most similar description
        k = 1  # Get top 1 match
        similarities, indices = faiss_index.search(query_embedding, k)
        
        if len(indices[0]) > 0:
            # Get the best match index and its similarity score
            best_match_idx = indices[0][0]
            similarity_score = similarities[0][0]
            
            # Map the index to the corresponding package ID
            best_package = str(best_match_idx)  # Package IDs are stored as string in the database
            
            print(f"Best matching package: {best_package} (similarity: {similarity_score:.4f})")
            return best_package
        else:
            print("No matches found, returning default package '0'")
            return '0'  # If no match, return '0' as default
            
    except Exception as e:
        print(f"Error in similarity search: {str(e)}")
        return '0'  # Return '0' in case of error


async def get_questions_by_package(package: str, limit: int = 15) -> List[Dict]:
    """Get questions from database filtered by package"""
    try:
        await db_service.connect()
        questions = await db_service.get_questions_by_package(package, limit)
        
        if not questions:
            print(f"No questions found for package: {package}, trying default")
            questions = await db_service.get_questions_by_package("basic", limit)
        
        if not questions:
            print("No questions found even for basic package")
            return []
        
        return questions[:limit]  # Limit to top 15 questions
        
    except Exception as e:
        print(f"Error getting questions by package: {str(e)}")
        return []

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

# Global session storage
session_managers = {}

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
        raise ValueError("Invalid format. Provide either an 'answers' array or 'question1'–'question11' keys.")
    
    return qa_pairs

def update_profile_from_qa(manager: SessionManager, qa_pairs: Dict[str, Any]):
    """Update user profile from Q&A pairs"""
    for i in range(1, len(PROFILING_QUESTIONS) + 1):
        question_key = f"question{i}"
        if question_key in qa_pairs:
            profile_key = QUESTION_KEYS[i - 1]  # Convert to 0-based index
            manager.update_profile_data(profile_key, qa_pairs[question_key])

def calculate_likert_average(scores: List[int]) -> float:
    """Calculate average of Likert scale responses"""
    if not scores:
        return 0.0
    
    valid_scores = [score for score in scores if isinstance(score, int) and 1 <= score <= 4]
    if not valid_scores:
        return 0.0
    
    return sum(valid_scores) / len(valid_scores)

async def evaluate_with_llm(manager: SessionManager) -> Dict[str, Any]:
    """Perform comprehensive evaluation using LLM"""
    try:
        questions = manager.context["test_questions"]
        answers = manager.context["test_answers"]
        user_profile = manager.context.get("user_profile", {}) if isinstance(manager.context.get("user_profile", {}), dict) else None
        # user_profile = ""
        # print(f"user_profile: {user_profile} (type: {type(user_profile)})")
        
        # Ensure user_profile is a dictionary
        if not isinstance(user_profile, dict):
            print("Error: user_profile is not a dictionary. Fallback to empty dictionary.")
            user_profile = ""  # Fallback to an empty dictionary
        
        # Proceed if it's a valid dictionary
        selected_package = manager.context["selected_package"]
        qa_pairs = manager.context.get("profiling_qa_pairs", {}) if isinstance(manager.context.get("profiling_qa_pairs", {}), dict) else {}
        likert_scores = manager.context.get("likert_scores", []) if isinstance(manager.context.get("likert_scores", []), list) else []
        
        # selected_package = "0"
        qa_pairs = {}
        # likert_scores = [random.randint(1, 4) for _ in range(len(questions))]  # Simulated scores


        # Calculate average score
        avg_score = calculate_likert_average(likert_scores)
        
        prompt = AssessmentPrompts.get_evaluation_prompt(
            user_profile, selected_package, qa_pairs, questions, answers, avg_score
        )
        
        ai_response = await llm_service.generate_response(prompt, [])
        
        # # Ensure the response is not empty and contains JSON
        # if ai_response and ai_response.strip().startswith("{") and ai_response.strip().endswith("}"):
        #     try:
        #         # Try parsing the JSON response
        #         evaluation = json.loads(ai_response)
        #     except json.JSONDecodeError as e:
        #         print(f"Error parsing JSON response: {str(e)}")
        #         return {"error": "Failed to parse evaluation response"}
        # else:
        #     print(f"Invalid or empty response from LLM: {ai_response}")
        #     return {"error": "No valid JSON response from LLM"}
        
        # Add calculated metrics
        # evaluation["likert_average"] = avg_score
        # evaluation["total_responses"] = len(likert_scores)
        
        return ai_response

    except Exception as e:
        print(f"Error during evaluation: {str(e)}")
        return {"error di main": str(e)}



resend.api_key = settings.MAIL_RESEND_API_KEY

def send_email(to: str, subject: str, body: str):
    """Send email notification using Resend"""
    try:
        params = {
            "from": "noreply@stelarea.com",
            "to": [to],
            "subject": subject,
            "html": body,
        }
        
        email = resend.Emails.send(params)
        
        print(f"Email sent successfully to {to}")
        print(f"Email ID: {email.get('id')}")
        return email
        
    except Exception as e:
        print(f"Failed to send email to {to}: {str(e)}")
        raise e

# Routes
@app.route('/', methods=['GET'])
def home():
    """API information"""
    return jsonify({
        "message": "Digital Forensics Readiness Assessment API",
        "version": "2.0",
        "features": ["Profiling", "FAISS Similarity Search", "Likert Scale Assessment", "LLM Evaluation"]
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
    """Process profiling answers, generate description, and find matching package"""
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
        
        # Generate profile description using LLM
        profile_description = await generate_profile_description(qa_pairs)
        
        # Find best matching package using FAISS similarity search
        print("Finding best matching package using FAISS...")
        selected_package = await find_best_package(profile_description)
        
        # Store results in session
        manager.context["profile_description"] = profile_description
        manager.context["selected_package"] = selected_package
        manager.context["current_phase"] = "package_selected"
        manager.context["profiling_qa_pairs"] = qa_pairs
        
        return jsonify({
            "session_id": manager.session_id,
            "profile_description": profile_description,
            "selected_package": selected_package,
            "current_phase": manager.context["current_phase"],
        })
        
    except Exception as e:
        print(f"Error in submit_answers: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/get_test_questions', methods=['GET'])
def get_test_questions():
    """Get test questions based on selected package"""
    try:
        manager = get_or_create_session()
        
        if manager.context["current_phase"] not in ["package_selected", "testing"]:
            return jsonify({"error": "Please complete profiling first"}), 400
        
        selected_package = manager.context.get("selected_package")
        if not selected_package:
            return jsonify({"error": "No package selected"}), 400
        
        print(f"Fetching questions for package: {selected_package}")
        
        # Gunakan MongoClient biasa
        client = MongoClient('mongodb://admin:securepassword123@mongodb:27017/cybersecurity_assessment?authSource=admin')
        db = client.cybersecurity_assessment
        
        # Menggunakan metode sinkron untuk mendapatkan data
        questions_cursor = db.questions.find({"package": selected_package}).limit(15)
        
        questions = []
        for question in questions_cursor:  # Iterasi menggunakan for biasa (sinkron)
            questions.append({
                "question": question.get("question"),
                "indikator": question.get("indikator"),
                "level": question.get("level"),
                # Include other fields as necessary
            })
        
        if not questions:
            return jsonify({"error": f"No questions found for package: {selected_package}"}), 404
        
        # Store questions in session
        manager.context["test_questions"] = questions
        manager.context["current_phase"] = "testing"
        
        return jsonify({
            "session_id": manager.session_id,
            "package": selected_package,
            "questions": questions,
            "questions_count": len(questions),
            "current_phase": manager.context["current_phase"],
            "instruction": "Please respond with numbers 1-4 for each question (Likert scale)"
        })
        
    except Exception as e:
        print(f"Error getting test questions: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/submit_test_answers', methods=['POST'])
def submit_test_answers():
    """Submit Likert scale test answers (1-4 scale)"""
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
        
        # Validate Likert scale answers (1-4)
        likert_scores = []
        for i, answer in enumerate(answers):
            try:
                score = int(answer)
                if score not in [1, 2, 3, 4]:
                    return jsonify({"error": f"Answer {i+1} must be 1, 2, 3, or 4"}), 400
                likert_scores.append(score)
            except (ValueError, TypeError):
                return jsonify({"error": f"Answer {i+1} must be a number (1-4)"}), 400
        
        # Store answers and scores
        manager.context["test_answers"] = answers
        manager.context["likert_scores"] = likert_scores
        manager.context["current_phase"] = "evaluation"
        
        # Calculate average score
        avg_score = calculate_likert_average(likert_scores)
        
        return jsonify({
            "session_id": manager.session_id,
            "current_phase": manager.context["current_phase"],
            "average_score": round(avg_score, 2),
            "total_responses": len(likert_scores),
            "score_distribution": {
                "1": likert_scores.count(1),
                "2": likert_scores.count(2), 
                "3": likert_scores.count(3),
                "4": likert_scores.count(4)
            }
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/submit_email', methods=['POST'])
def submit_email():
    """Submit user email for notifications"""
    try:
        manager = get_or_create_session()
        
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
        
        data = request.get_json()
        email = data.get('email')
        
        if not email or '@' not in email:
            return jsonify({"error": "Invalid email address"}), 400
        
        # Store email in user profile
        manager.context["user_profile"]["email"] = email
        
        return jsonify({
            "session_id": manager.session_id,
            "email": email,
            "message": "Email submitted successfully"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get_results', methods=['GET'])
@async_route
async def get_results():
    """Get final evaluation and recommendations using LLM"""
    import json  # Move import to top level
    
    try:
        manager = get_or_create_session()
        
        current_phase = manager.context.get('current_phase')
        print(f"Current phase: {current_phase}")
        
        if current_phase == "evaluation":
            # Perform LLM evaluation
            print("Performing LLM evaluation...")
            evaluation = await evaluate_with_llm(manager)
            
            # Store final evaluation
            manager.context["final_evaluation"] = evaluation
            manager.context["current_phase"] = "completed"

            # Get user profile and email safely
            user_profile = manager.context.get("user_profile", {})
            
            # Ensure user_profile is a dictionary
            if not isinstance(user_profile, dict):
                if isinstance(user_profile, str):
                    try:
                        user_profile = json.loads(user_profile)
                    except (json.JSONDecodeError, ValueError):
                        user_profile = {}
                else:
                    user_profile = {}

            # Get email safely
            user_email = user_profile.get("email") if isinstance(user_profile, dict) else None

            # Send email if available
            if user_email:
                email_subject = "Digital Forensic Readiness (DFR) Test Results"
                email_body = generate_email_template(manager)
                try:
                    print(f"Sending email to: {user_email}")
                    send_email(user_email, email_subject, email_body)
                    print("Email sent successfully")
                except Exception as e:
                    print(f"Failed to send email: {str(e)}")
            else:
                print("Email not provided.")
                return jsonify({
                    "error": "Email not provided. Please submit your email to receive results."
                })
            
            # Parse evaluation if it's a JSON string
            evaluation = manager.context["final_evaluation"]
            if isinstance(evaluation, str):
                try:
                    evaluation = json.loads(evaluation)
                except (json.JSONDecodeError, ValueError):
                    # If parsing fails, keep as string but wrap in object
                    evaluation = {"detailed_analysis": evaluation}
            
            # Return evaluation results
            return jsonify({
                "session_id": manager.session_id,
                "selected_package": manager.context.get("selected_package"),
                "profile_description": manager.context.get("profile_description"),
                "user_profile": user_profile,
                "profiling_qa": manager.context.get("profiling_qa_pairs", {}),
                "test_questions": len(manager.context.get("test_questions", [])),
                "evaluation": evaluation,  # Now parsed as object
                "questions_answered": len(manager.context.get("test_answers", [])),
                "current_phase": manager.context["current_phase"],
                "assessment_complete": True,
                "timestamp": datetime.now().isoformat()
            })
            
        elif current_phase == "completed":
            # Already completed, return cached results
            user_profile = manager.context.get("user_profile", {})
            
            # Ensure user_profile is a dictionary for cached results too
            if not isinstance(user_profile, dict):
                if isinstance(user_profile, str):
                    try:
                        user_profile = json.loads(user_profile)
                    except (json.JSONDecodeError, ValueError):
                        user_profile = {}
                else:
                    user_profile = {}
            
            # Parse cached evaluation too
            evaluation = manager.context.get("final_evaluation")
            if isinstance(evaluation, str):
                try:
                    evaluation = json.loads(evaluation)
                except (json.JSONDecodeError, ValueError):
                    evaluation = {"detailed_analysis": evaluation}
            
            return jsonify({
                "session_id": manager.session_id,
                "selected_package": manager.context.get("selected_package"),
                "profile_description": manager.context.get("profile_description"),
                "user_profile": user_profile,
                "profiling_qa": manager.context.get("profiling_qa_pairs", {}),
                "test_questions": len(manager.context.get("test_questions", [])),
                "evaluation": evaluation,  # Now parsed as object
                "questions_answered": len(manager.context.get("test_answers", [])),
                "current_phase": current_phase,
                "assessment_complete": True,
                "timestamp": datetime.now().isoformat()
            })
        else:
            print("Test answers not submitted.")
            return jsonify({"error": "Please submit test answers first"}), 400
        
    except Exception as e:
        print(f"Error in get_results: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error in get_results": str(e)}), 500
    
@app.route('/session_status', methods=['GET'])
def session_status():
    """Get current session status"""
    try:
        manager = get_or_create_session()
        return jsonify({
            "session_id": manager.session_id,
            "current_phase": manager.context["current_phase"],
            "selected_package": manager.context.get("selected_package"),
            "profile_description": manager.context.get("profile_description", ""),
            "profiling_progress": f"{manager.context['profiling_progress']}/{manager.context['total_profiling_questions']}",
            "created_at": manager.created_at.isoformat(),
            "questions_available": len(manager.context.get("test_questions", [])),
            "answers_submitted": len(manager.context.get("test_answers", [])),
            "average_score": round(calculate_likert_average(manager.context.get("likert_scores", [])), 2) if manager.context.get("likert_scores") else 0.0
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

@app.route('/check_db', methods=['GET'])
def check_db():
    try:
        client = MongoClient('mongodb://admin:securepassword123@mongodb:27017/cybersecurity_assessment?authSource=admin')
        db = client.cybersecurity_assessment
        keterangan_count = db.keterangan.count_documents({})
        questions_count = db.questions.count_documents({})
        return jsonify({
            "keterangan_count": keterangan_count,
            "questions_count": questions_count
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
from bson import ObjectId

from flask import Flask, jsonify
from pymongo import MongoClient
from bson import ObjectId  # Import ObjectId to handle serialization
def json_serialize(doc):
    """Convert MongoDB document to JSON-serializable format"""
    if isinstance(doc, dict):
        for key, value in doc.items():
            if isinstance(value, ObjectId):
                doc[key] = str(value)  # Convert ObjectId to string
    return doc

@app.route('/get_keterangan', methods=['GET'])
def get_keterangan():
    try:
        # Connect to MongoDB
        client = MongoClient('mongodb://admin:securepassword123@mongodb:27017/cybersecurity_assessment?authSource=admin')
        db = client.cybersecurity_assessment
        
        # Find documents with package == "0"
        keterangan = db.questions.find({"package": "0"})
        
        # Convert the cursor to a list
        keterangan_list = list(keterangan)
        
        if keterangan_list:
            # Convert ObjectId to string for JSON serialization
            return jsonify([json_serialize(doc) for doc in keterangan_list])
        else:
            return jsonify({"message": "No keterangan found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Timeline Profiling Questions
TIMELINE_PROFILING_QUESTIONS = [
    {
        "type": "target",
        "question": "Dalam berapa bulan organisasi Anda ingin mencapai peningkatan kapabilitas DFR?",
        "choices": [
            {"label": "3-6 bulan (Fast Track)"},
            {"label": "6-12 bulan (Standard)"},
            {"label": "12-18 bulan (Comprehensive)"},
            {"label": "18-24 bulan (Strategic)"}
        ]
    },
    {
        "type": "priority",
        "question": "Apa prioritas utama organisasi dalam pengembangan DFR?",
        "choices": [
            {"label": "Compliance dan regulasi"},
            {"label": "Incident response capability"},
            {"label": "Evidence collection & preservation"},
            {"label": "Forensic analysis capability"},
            {"label": "Semua aspek secara seimbang"}
        ]
    },
    {
        "type": "resource",
        "question": "Berapa budget yang dapat dialokasikan untuk pengembangan DFR per tahun?",
        "choices": [
            {"label": "< 100 juta"},
            {"label": "100-500 juta"},
            {"label": "500 juta - 1 miliar"},
            {"label": "1-5 miliar"},
            {"label": "> 5 miliar"}
        ]
    },
    {
        "type": "resource",
        "question": "Apakah organisasi memiliki tim IT Security/Cybersecurity yang dedicated?",
        "choices": [
            {"label": "Tidak ada sama sekali"},
            {"label": "Ada, kurang dari 3 orang"},
            {"label": "Ada, 3-10 orang"},
            {"label": "Ada, lebih dari 10 orang"},
            {"label": "Ada departemen tersendiri"}
        ]
    },
    {
        "type": "capability",
        "question": "Apakah organisasi sudah memiliki tools/software untuk forensik digital?",
        "choices": [
            {"label": "Belum ada sama sekali"},
            {"label": "Ada tools basic (free/open source)"},
            {"label": "Ada beberapa commercial tools"},
            {"label": "Ada suite lengkap forensic tools"},
            {"label": "Ada platform forensik enterprise"}
        ]
    },
    {
        "type": "capability",
        "question": "Apakah organisasi sudah memiliki prosedur/SOP untuk incident response?",
        "choices": [
            {"label": "Belum ada"},
            {"label": "Ada draft/belum formal"},
            {"label": "Ada dan sudah formal"},
            {"label": "Ada dan rutin diupdate"},
            {"label": "Ada dan sudah terintegrasi dengan business continuity"}
        ]
    },
    {
        "type": "training",
        "question": "Berapa orang yang bisa dialokasikan untuk training/sertifikasi DFR?",
        "choices": [
            {"label": "Tidak ada"},
            {"label": "1-2 orang"},
            {"label": "3-5 orang"},
            {"label": "6-10 orang"},
            {"label": "> 10 orang"}
        ]
    },
    {
        "type": "urgency",
        "question": "Seberapa urgent kebutuhan DFR untuk organisasi Anda?",
        "choices": [
            {"label": "Nice to have - untuk persiapan masa depan"},
            {"label": "Important - ada rencana implementasi"},
            {"label": "Urgent - ada requirement compliance"},
            {"label": "Critical - sudah pernah ada incident"},
            {"label": "Emergency - sedang ada incident/investigasi"}
        ]
    },
    {
        "type": "infrastructure",
        "question": "Bagaimana kondisi infrastruktur IT organisasi saat ini?",
        "choices": [
            {"label": "Basic - minimal infrastructure"},
            {"label": "Standard - ada server dan network management"},
            {"label": "Advanced - ada monitoring dan logging"},
            {"label": "Enterprise - ada SIEM dan security tools"},
            {"label": "Mature - fully integrated security infrastructure"}
        ]
    },
    {
        "type": "commitment",
        "question": "Apakah top management mendukung penuh initiative DFR ini?",
        "choices": [
            {"label": "Belum aware tentang DFR"},
            {"label": "Aware tapi belum prioritas"},
            {"label": "Supportive tapi budget terbatas"},
            {"label": "Fully supportive dengan budget adequate"},
            {"label": "Champion - DFR adalah strategic priority"}
        ]
    }
]

TIMELINE_QUESTION_KEYS = [
    "timeline_duration", "priority_focus", "budget_allocation", 
    "security_team", "forensic_tools", "incident_procedures",
    "training_capacity", "urgency_level", "infrastructure_maturity", 
    "management_support"
]

@app.route('/start_profiling_timeline', methods=['GET'])
def start_profiling_timeline():
    """Start timeline profiling - return questions for roadmap generation"""
    try:
        manager = get_or_create_session()
        
        # Check if assessment is completed
        if manager.context.get("current_phase") != "completed":
            return jsonify({
                "error": "Please complete the assessment first before generating timeline"
            }), 400
        
        # Initialize timeline profiling context
        manager.context["timeline_profiling_progress"] = 0
        manager.context["timeline_profiling_data"] = {}
        manager.context["current_phase"] = "timeline_profiling"
        
        return jsonify({
            "session_id": manager.session_id,
            "message": "Timeline profiling started",
            "questions": TIMELINE_PROFILING_QUESTIONS,
            "total_questions": len(TIMELINE_PROFILING_QUESTIONS),
            "current_phase": manager.context["current_phase"],
            "instruction": "Please answer all questions to generate your customized roadmap"
        })
        
    except Exception as e:
        print(f"Error in start_profiling_timeline: {str(e)}")
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


async def generate_timeline_with_profiling(manager: SessionManager, timeline_answers: Dict[str, Any]) -> Dict[str, Any]:
    """Generate timeline roadmap based on assessment results and timeline profiling"""
    
    # Get assessment data
    final_evaluation = manager.context.get("final_evaluation", {})
    if isinstance(final_evaluation, str):
        try:
            final_evaluation = json.loads(final_evaluation)
        except (json.JSONDecodeError, ValueError):
            final_evaluation = {}
    
    current_level = final_evaluation.get("current_level", "Level 0")
    avg_score = manager.context.get("likert_scores", [])
    avg_score = calculate_likert_average(avg_score) if avg_score else 0.0
    
    selected_package = manager.context.get("selected_package", "0")
    user_profile = manager.context.get("user_profile", {})
    
    # Build profile summary
    profile_info = []
    if isinstance(user_profile, dict):
        for key, value in user_profile.items():
            if key != "email":
                profile_info.append(f"{key}: {value}")
    profile_summary = "\n".join(profile_info) if profile_info else "No profile data"
    
    # Build timeline profiling summary
    timeline_profile = []
    for i, (key, answer) in enumerate(timeline_answers.items()):
        question = TIMELINE_PROFILING_QUESTIONS[i]["question"]
        timeline_profile.append(f"{key}: {answer}")
    timeline_summary = "\n".join(timeline_profile)
    
    # Parse duration from answer
    duration_text = timeline_answers.get("timeline_duration", "")
    if "3-6" in duration_text:
        target_months = 6
    elif "6-12" in duration_text:
        target_months = 12
    elif "12-18" in duration_text:
        target_months = 18
    elif "18-24" in duration_text:
        target_months = 24
    else:
        target_months = 12  # default
    
    # Generate comprehensive prompt
    timeline_prompt = f"""
Sebagai expert Digital Forensic Readiness (DFR), buatlah roadmap pengembangan kapabilitas DFR yang komprehensif, realistis, dan customized.

DATA ASSESSMENT HASIL:
- Current Level: {current_level}
- Average Score: {avg_score:.2f}/4.0
- Package Used: {selected_package}

PROFIL ORGANISASI:
{profile_summary}

HASIL PROFILING ROADMAP:
{timeline_summary}

TARGET DURATION: {target_months} bulan

TUGAS ANDA:
Berdasarkan SEMUA data di atas, buatlah roadmap yang:
1. REALISTIS sesuai budget, resources, dan timeline yang disebutkan
2. SPESIFIK dengan tasks yang actionable dan measurable
3. PROGRESSIVE dengan phases yang jelas
4. COMPREHENSIVE mencakup people, process, technology
5. ALIGNED dengan prioritas dan urgency yang disebutkan

Format JSON yang HARUS diikuti (STRICT):

{{
  "current_assessment": {{
    "current_level": "{current_level}",
    "level_description": "deskripsi detail kondisi saat ini berdasarkan assessment",
    "score": {avg_score:.2f},
    "maturity_areas": {{
      "policy_procedures": "status dan deskripsi",
      "technical_capability": "status dan deskripsi",
      "people_skills": "status dan deskripsi",
      "tools_infrastructure": "status dan deskripsi"
    }},
    "strengths": ["kekuatan spesifik 1", "kekuatan spesifik 2", "kekuatan spesifik 3"],
    "weaknesses": ["kelemahan spesifik 1", "kelemahan spesifik 2", "kelemahan spesifik 3"]
  }},
  
  "target_roadmap": {{
    "target_level": "Level yang realistis untuk dicapai",
    "target_level_description": "deskripsi detail target capability",
    "estimated_duration_months": {target_months},
    "justification": "penjelasan detail kenapa target ini realistis berdasarkan kondisi organisasi (budget, resources, urgency)",
    "key_improvements": ["improvement area 1", "improvement area 2", "improvement area 3"]
  }},
  
  "timeline": [
    {{
      "phase": 1,
      "phase_name": "Foundation & Quick Wins",
      "duration_months": 3,
      "start_month": 1,
      "end_month": 3,
      "objectives": [
        "objektif strategis 1",
        "objektif strategis 2",
        "objektif strategis 3"
      ],
      "focus_areas": ["focus area 1", "focus area 2"],
      "milestones": [
        {{
          "month": 1,
          "month_name": "Januari 2025",
          "title": "Initial Setup & Assessment",
          "description": "Deskripsi singkat milestone ini",
          "tasks": [
            "Task spesifik dan actionable 1",
            "Task spesifik dan actionable 2",
            "Task spesifik dan actionable 3",
            "Task spesifik dan actionable 4"
          ],
          "deliverables": [
            "Deliverable konkret 1",
            "Deliverable konkret 2"
          ],
          "kpis": [
            "KPI measurable 1 (dengan target angka)",
            "KPI measurable 2 (dengan target angka)"
          ],
          "responsible_roles": ["role 1", "role 2"],
          "dependencies": ["dependency jika ada"]
        }},
        {{
          "month": 2,
          "month_name": "Februari 2025",
          "title": "Foundation Implementation",
          "description": "Deskripsi singkat",
          "tasks": ["task 1", "task 2", "task 3", "task 4"],
          "deliverables": ["deliverable 1", "deliverable 2"],
          "kpis": ["KPI 1", "KPI 2"],
          "responsible_roles": ["role 1"],
          "dependencies": ["Completion of Month 1 milestones"]
        }},
        {{
          "month": 3,
          "month_name": "Maret 2025",
          "title": "Phase 1 Consolidation",
          "description": "Deskripsi singkat",
          "tasks": ["task 1", "task 2", "task 3"],
          "deliverables": ["deliverable 1", "deliverable 2"],
          "kpis": ["KPI 1", "KPI 2"],
          "responsible_roles": ["role 1"],
          "dependencies": ["dependencies"]
        }}
      ],
      "phase_deliverables": ["major deliverable 1", "major deliverable 2"],
      "success_criteria": ["criteria 1", "criteria 2"]
    }},
    {{
      "phase": 2,
      "phase_name": "Implementation & Capability Building",
      "duration_months": (sesuaikan dengan target_months),
      "start_month": 4,
      "end_month": (sesuaikan),
      "objectives": ["objektif 1", "objektif 2"],
      "focus_areas": ["focus 1", "focus 2"],
      "milestones": [
        {{
          "month": 4,
          "month_name": "April 2025",
          "title": "...",
          "description": "...",
          "tasks": ["..."],
          "deliverables": ["..."],
          "kpis": ["..."],
          "responsible_roles": ["..."],
          "dependencies": ["..."]
        }}
        // Continue for all months in phase 2
      ],
      "phase_deliverables": ["..."],
      "success_criteria": ["..."]
    }},
    {{
      "phase": 3,
      "phase_name": "Optimization & Sustainability",
      "duration_months": (sesuaikan),
      "start_month": (sesuaikan),
      "end_month": {target_months},
      "objectives": ["objektif 1", "objektif 2"],
      "focus_areas": ["focus 1", "focus 2"],
      "milestones": [
        // milestones untuk phase terakhir sampai bulan ke-{target_months}
      ],
      "phase_deliverables": ["..."],
      "success_criteria": ["..."]
    }}
  ],
  
  "resource_requirements": {{
    "budget_estimate": {{
      "total_idr": "Rp XXX juta - berdasarkan budget allocation yang disebutkan",
      "total_idr_numeric": 000000000,
      "breakdown": {{
        "technology_tools": {{
          "amount": "Rp XXX juta",
          "percentage": "XX%",
          "items": ["item 1", "item 2"]
        }},
        "training_certification": {{
          "amount": "Rp XXX juta",
          "percentage": "XX%",
          "items": ["item 1", "item 2"]
        }},
        "personnel_recruitment": {{
          "amount": "Rp XXX juta",
          "percentage": "XX%",
          "items": ["item 1"]
        }},
        "consulting_services": {{
          "amount": "Rp XXX juta",
          "percentage": "XX%",
          "items": ["item 1"]
        }},
        "infrastructure": {{
          "amount": "Rp XXX juta",
          "percentage": "XX%",
          "items": ["item 1", "item 2"]
        }}
      }},
      "notes": "Catatan tentang budget (misalnya jika budget terbatas, fokus di area mana)"
    }},
    
    "human_resources": [
      {{
        "role": "DFR Program Manager",
        "count": 1,
        "commitment": "Full-time/Part-time",
        "required_skills": ["skill 1", "skill 2", "skill 3"],
        "responsibilities": ["tanggung jawab detail 1", "tanggung jawab detail 2"],
        "can_be_existing_staff": true/false,
        "training_needed": ["training 1 jika ada"]
      }},
      {{
        "role": "Digital Forensic Analyst",
        "count": (sesuaikan dengan training_capacity),
        "commitment": "...",
        "required_skills": ["..."],
        "responsibilities": ["..."],
        "can_be_existing_staff": true/false,
        "training_needed": ["..."]
      }}
      // tambahkan roles lain sesuai kebutuhan
    ],
    
    "technology_stack": [
      {{
        "category": "Forensic Investigation Tools",
        "priority": "High/Medium/Low",
        "items": [
          {{
            "name": "Tool Name (disesuaikan dengan forensic_tools status)",
            "purpose": "purpose spesifik",
            "estimated_cost": "Rp XXX juta atau Free/Open Source",
            "implementation_timeline": "Month X-Y"
          }}
        ]
      }},
      {{
        "category": "Infrastructure & Storage",
        "priority": "High",
        "items": [
          {{
            "name": "...",
            "purpose": "...",
            "estimated_cost": "...",
            "implementation_timeline": "..."
          }}
        ]
      }},
      {{
        "category": "Security & Monitoring",
        "priority": "Medium/High",
        "items": ["..."]
      }}
    ],
    
    "training_plan": {{
      "internal_training": [
        {{
          "topic": "DFR Fundamentals",
          "target_audience": "All IT staff",
          "duration": "X days",
          "schedule": "Month Y",
          "estimated_cost": "Rp XXX"
        }}
      ],
      "external_certification": [
        {{
          "certification": "Cert Name",
          "target_roles": ["role 1"],
          "provider": "provider name",
          "duration": "X days",
          "schedule": "Month Y",
          "estimated_cost_per_person": "Rp XXX"
        }}
      ],
      "total_training_budget": "Rp XXX juta"
    }}
  }},
  
  "risk_mitigation": [
    {{
      "risk_id": "R001",
      "risk": "Deskripsi risiko spesifik berdasarkan profiling",
      "category": "Technical/Resource/Organizational",
      "impact": "High/Medium/Low",
      "probability": "High/Medium/Low",
      "risk_score": "Impact x Probability score",
      "mitigation_strategy": "Strategi detail dan actionable",
      "contingency_plan": "Rencana jika risiko terjadi",
      "owner": "Role yang responsible"
    }}
    // minimal 5-7 risks yang relevan
  ],
  
  "success_criteria": [
    {{
      "criteria": "Kriteria sukses spesifik dan measurable",
      "measurement": "Cara pengukuran",
      "target": "Target value/status",
      "timeline": "Month X"
    }}
  ],
  
  "governance": {{
    "steering_committee": {{
      "members": ["role 1", "role 2"],
      "meeting_frequency": "Monthly/Quarterly",
      "responsibilities": ["tanggung jawab 1", "tanggung jawab 2"]
    }},
    "reporting_structure": {{
      "regular_reports": "Frequency dan format",
      "stakeholder_updates": "Frequency dan audience",
      "escalation_process": "Process untuk issues"
    }},
    "quality_assurance": {{
      "review_points": ["checkpoint 1", "checkpoint 2"],
      "audit_schedule": "Schedule untuk audit"
    }}
  }},
  
  "quick_wins": [
    {{
      "title": "Quick win yang bisa immediate impact",
      "description": "Deskripsi detail",
      "timeline": "Week 1-2",
      "effort": "Low/Medium",
      "impact": "High/Medium",
      "resources_needed": ["resource 1"]
    }}
    // 3-5 quick wins
  ],
  
  "dependencies_external": [
    {{
      "dependency": "External dependency yang perlu diperhatikan",
      "type": "Vendor/Regulatory/Partner",
      "impact_if_delayed": "Impact description",
      "mitigation": "Cara handle jika terlambat"
    }}
  ]
}}

CRITICAL INSTRUCTIONS:
1. Response HANYA JSON - no markdown, no backticks, no additional text
2. SEMUA bulan dari 1 sampai {target_months} HARUS ada milestones
3. Tasks HARUS spesifik, actionable, dan measurable - NO GENERIC TASKS
4. Budget HARUS realistis sesuai dengan budget_allocation yang disebutkan
5. Number of people HARUS sesuai dengan training_capacity dan security_team
6. Tools/technology HARUS sesuai dengan forensic_tools status (don't suggest expensive tools if budget low)
7. Urgency level HARUS reflected dalam timeline dan priority
8. Management support level HARUS reflected dalam governance structure
9. Infrastructure maturity HARUS considered dalam technology recommendations
10. Priority focus HARUS jelas terlihat di semua phases

Generate complete, realistic, dan immediately actionable roadmap!
"""

    try:
        print("Generating timeline with LLM based on profiling...")
        timeline_response = await llm_service.generate_response(timeline_prompt, [])
        
        # Clean and parse response
        timeline_response = timeline_response.strip()
        if timeline_response.startswith("```"):
            lines = timeline_response.split("\n")
            timeline_response = "\n".join([l for l in lines if not l.startswith("```")])
        
        # Assuming timeline_response is the raw response string
        try:
            # Step 1: Parse the outer JSON
            outer_data = json.loads(timeline_response)
            
            # Step 2: Parse the inner 'timeline' JSON string
            inner_timeline = json.loads(outer_data['timeline'])

            # Now you have both the outer data and the parsed timeline
            print("Parsed timeline:", inner_timeline)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {str(e)}")
            print(f"Problematic response: {timeline_response}")
            return {"error": "Unable to parse timeline response"}
        return timeline_response
        
    except Exception as e:
        print(f"Error generating timeline: {str(e)}")
        raise e


@app.route('/get_timeline', methods=['POST'])
@async_route
async def get_timeline():
    """Generate timeline roadmap based on profiling answers"""
    try:
        manager = get_or_create_session()
        
        # Validate phase
        if manager.context.get("current_phase") != "timeline_profiling":
            return jsonify({
                "error": "Please start timeline profiling first using /start_profiling_timeline"
            }), 400
        
        # Validate request
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
        
        data = request.get_json()
        
        # Parse timeline profiling answers
        try:
            timeline_answers = parse_timeline_answers(data)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        
        # Store timeline profiling data
        manager.context["timeline_profiling_data"] = timeline_answers
        manager.context["timeline_profiling_progress"] = len(timeline_answers)
        
        # Generate timeline with LLM
        print("Generating comprehensive timeline roadmap...")
        timeline_data = await generate_timeline_with_profiling(manager, timeline_answers)
        
        # Store timeline data
        manager.context["timeline_data"] = timeline_data
        manager.context["current_phase"] = "timeline_generated"
        
        # Return complete response
        return jsonify({
            "session_id": manager.session_id,
            "timeline_generated": True,
            "current_phase": manager.context["current_phase"],
            "profiling_data": timeline_answers,
            "timeline": timeline_data,
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "assessment_date": manager.created_at.isoformat(),
                "package_used": manager.context.get("selected_package", "0"),
                "timeline": timeline_data
            }
        })
        
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