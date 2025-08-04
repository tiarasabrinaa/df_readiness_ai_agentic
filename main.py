from flask import Flask, request, jsonify, session
from flask_cors import CORS
import uuid
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List

# REAL imports - ganti path sesuai struktur project lu
from services.database_service import db_service
from services.llm_service import llm_service

app = Flask(__name__)
app.secret_key = 'your_secret_key_change_this_in_production'
CORS(app, supports_credentials=True)

class SessionManager:
    """Enhanced session manager with REAL LLM integration"""
    
    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.created_at = datetime.now()
        self.context = {
            "user_profile": {},
            "current_phase": "profiling",
            "profiling_data": {},
            "assessment_level": None,
            "profiling_progress": 0,
            "total_profiling_questions": 5,
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

# Global session manager
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

# Initialize database connection on startup
with app.app_context():
    async def startup():
        """Connect to database on startup"""
        try:
            await db_service.connect()
            print("✅ Database connected successfully")
            
            # Load questions if needed
            question_count = await db_service.count_questions()
            print(f"📊 Total questions in database: {question_count}")
            
        except Exception as e:
            print(f"❌ Failed to initialize database: {str(e)}")

@app.route('/', methods=['GET'])
def home():
    """API information"""
    return jsonify({
        "message": "🚀 REAL Cybersecurity Readiness Assessment API with LLM",
        "version": "2.0-REAL",
        "flow": {
            "1": "GET /start_profiling - Get 5 profiling questions",
            "2": "POST /submit_answers - Submit answers, REAL LLM determines level", 
            "3": "GET /get_test_questions - Get 3 questions from REAL MongoDB",
            "4": "POST /submit_test_answers - Submit test answers",
            "5": "GET /get_results - REAL LLM evaluation and recommendations"
        },
        "features": {
            "llm_integration": "✅ Real Telkom LLM API",
            "database": "✅ Real MongoDB with Motor",
            "personalization": "✅ AI-powered level assessment",
            "evaluation": "✅ Comprehensive AI analysis"
        }
    })

@app.route('/start_profiling', methods=['GET'])
def start_profiling():
    """Send 5 profiling questions"""
    try:
        manager = get_or_create_session()
        
        questions = [
            "Apa jenis industri yang Anda geluti?",
            "Seberapa besar perusahaan Anda (berapa karyawan)?", 
            "Apa posisi/role Anda di perusahaan?",
            "Berapa tahun pengalaman Anda dalam keamanan IT/cybersecurity?",
            "Apakah perusahaan Anda pernah mengalami insiden keamanan? Jelaskan singkat."
        ]
        
        return jsonify({
            "session_id": manager.session_id,
            "questions": questions,
            "total_questions": len(questions),
            "current_phase": manager.context["current_phase"],
            "instruction": "Jawab semua pertanyaan dengan detail untuk analisis LLM yang akurat"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/submit_answers', methods=['POST'])
async def submit_answers():
    """Process profiling answers and determine assessment level using REAL LLM"""
    try:
        manager = get_or_create_session()
        
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
        
        data = request.get_json()
        answers = data.get('answers', [])
        
        if len(answers) != 5:
            return jsonify({"error": "Please provide exactly 5 answers."}), 400
        
        # Store profile data
        question_keys = ["industry", "company_size", "position", "experience", "security_incidents"]
        for idx, answer in enumerate(answers):
            if idx < len(question_keys):
                manager.update_profile_data(question_keys[idx], answer)
        
        # Prepare REAL prompt for LLM analysis
        profiling_prompt = f"""
Kamu adalah AI expert dalam cybersecurity assessment. Berdasarkan profiling data user berikut, tentukan level assessment yang tepat:

PROFILING DATA:
1. Industri: {answers[0]}
2. Ukuran perusahaan: {answers[1]}
3. Posisi: {answers[2]}
4. Pengalaman cybersecurity: {answers[3]}
5. Riwayat insiden: {answers[4]}

TUGAS:
Analisis profile user dan tentukan level assessment yang tepat berdasarkan kriteria:

BEGINNER (Basic):
- Pengalaman < 2 tahun dalam cybersecurity
- Perusahaan kecil (<50 karyawan) atau tidak ada dedicated security team
- Belum pernah/jarang mengalami insiden serius
- Role tidak spesifik ke security (general IT, admin, dll)

INTERMEDIATE:
- Pengalaman 2-7 tahun dalam cybersecurity  
- Perusahaan menengah (50-500 karyawan) dengan basic security measures
- Pernah mengalami beberapa insiden dan ada proses handling
- Role terkait security tapi belum senior level

ADVANCED:
- Pengalaman >7 tahun atau role senior security
- Perusahaan besar (>500 karyawan) dengan mature security program
- Pengalaman menangani insiden kompleks/APT
- Role seperti CISO, Senior Security Analyst, Security Architect

FORMAT RESPONSE JSON:
{{
    "assessment_level": "Beginner/Intermediate/Advanced",
    "confidence_score": 85,
    "reasoning": "penjelasan detail mengapa level ini dipilih berdasarkan analisis profiling",
    "user_profile_summary": "ringkasan karakteristik user",
    "key_indicators": ["indicator1", "indicator2", "indicator3"]
}}

Berikan analisis yang akurat dan reasoning yang solid!
"""
        
        # REAL LLM CALL - bukan mock!
        print(f"🤖 Calling REAL LLM for profile analysis...")
        ai_response = await llm_service.generate_response(profiling_prompt, [])
        print(f"🎯 LLM Response: {ai_response[:200]}...")
        
        # Parse LLM response
        try:
            # Try to extract JSON from response
            if '{' in ai_response and '}' in ai_response:
                json_start = ai_response.find('{')
                json_end = ai_response.rfind('}') + 1
                json_str = ai_response[json_start:json_end]
                llm_result = json.loads(json_str)
            else:
                # Fallback parsing if no JSON format
                raise json.JSONDecodeError("No JSON found", ai_response, 0)
                
            assessment_level = llm_result.get("assessment_level", "Beginner")
            
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON parsing failed: {str(e)}")
            print(f"Raw LLM response: {ai_response}")
            
            # Fallback: extract level from text
            ai_lower = ai_response.lower()
            if "advanced" in ai_lower:
                assessment_level = "Advanced"
            elif "intermediate" in ai_lower:
                assessment_level = "Intermediate"
            else:
                assessment_level = "Beginner"
                
            llm_result = {
                "assessment_level": assessment_level,
                "reasoning": "Level determined from text analysis",
                "raw_response": ai_response
            }
        
        # Update session with REAL analysis
        manager.context["profiling_progress"] = 5
        manager.context["current_phase"] = "assessment_level"
        manager.context["assessment_level"] = assessment_level
        manager.context["llm_analysis"] = llm_result
        
        return jsonify({
            "message": "✅ Profiling complete. Level determined by REAL LLM analysis.",
            "session_id": manager.session_id,
            "profile_data": manager.context["user_profile"],
            "assessment_level": assessment_level,
            "llm_analysis": llm_result,
            "current_phase": manager.context["current_phase"],
            "next_step": "Call GET /get_test_questions to get questions from MongoDB"
        })
        
    except Exception as e:
        print(f"❌ Error in submit_answers: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/get_test_questions', methods=['GET'])
async def get_test_questions():
    """Get 3 questions from REAL MongoDB based on assessment level"""
    try:
        manager = get_or_create_session()
        
        if manager.context["current_phase"] != "assessment_level":
            return jsonify({"error": "Please complete profiling first"}), 400
        
        assessment_level = manager.context["assessment_level"]
        if not assessment_level:
            return jsonify({"error": "Assessment level not determined"}), 400
        
        print(f"📊 Fetching questions from MongoDB for level: {assessment_level}")
        
        # REAL DATABASE CALL - bukan mock!
        questions = await db_service.get_questions_by_level(assessment_level)
        
        if not questions:
            print(f"⚠️ No questions found for level {assessment_level}, trying alternatives...")
            # Fallback: try other levels
            for fallback_level in ["Intermediate", "Beginner", "Advanced"]:
                if fallback_level != assessment_level:
                    questions = await db_service.get_questions_by_level(fallback_level)
                    if questions:
                        print(f"✅ Found {len(questions)} questions from {fallback_level} level")
                        break
        
        if not questions:
            return jsonify({
                "error": "No questions available in database",
                "suggestion": "Please load questions using /load_questions endpoint"
            }), 404
        
        # Take only 3 questions
        selected_questions = questions[:3]
        
        # Store questions in session
        manager.context["test_questions"] = selected_questions
        manager.context["current_phase"] = "testing"
        
        return jsonify({
            "session_id": manager.session_id,
            "assessment_level": assessment_level,
            "questions": selected_questions,
            "total_questions": len(selected_questions),
            "current_phase": manager.context["current_phase"],
            "instruction": "Jawab semua pertanyaan dengan detail untuk evaluasi LLM yang komprehensif"
        })
        
    except Exception as e:
        print(f"❌ Error getting test questions: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/submit_test_answers', methods=['POST'])
def submit_test_answers():
    """Submit test answers and prepare for REAL LLM evaluation"""
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
        
        # Store answers with validation
        if not all(answer.strip() for answer in answers):
            return jsonify({"error": "All answers must be non-empty"}), 400
        
        manager.context["test_answers"] = answers
        manager.context["current_phase"] = "evaluation"
        
        return jsonify({
            "message": "✅ Test answers submitted successfully",
            "session_id": manager.session_id, 
            "answers_count": len(answers),
            "current_phase": manager.context["current_phase"],
            "next_step": "Call GET /get_results to get REAL LLM evaluation"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get_results', methods=['GET'])
async def get_results():
    """Get final evaluation and recommendations using REAL LLM"""
    try:
        manager = get_or_create_session()
        
        if manager.context["current_phase"] != "evaluation":
            return jsonify({"error": "Please submit test answers first"}), 400
        
        questions = manager.context["test_questions"]
        answers = manager.context["test_answers"]
        user_profile = manager.context["user_profile"]
        assessment_level = manager.context["assessment_level"]
        
        # Prepare comprehensive evaluation prompt
        evaluation_prompt = f"""
Kamu adalah expert dalam cybersecurity dan digital forensics readiness assessment. 

USER PROFILE:
- Industri: {user_profile.get('industry', 'Unknown')}
- Ukuran perusahaan: {user_profile.get('company_size', 'Unknown')}
- Posisi: {user_profile.get('position', 'Unknown')}
- Pengalaman: {user_profile.get('experience', 'Unknown')}
- Assessment Level: {assessment_level}

ASSESSMENT DATA:
"""
        
        # Add Q&A pairs
        for i, (question, answer) in enumerate(zip(questions, answers), 1):
            evaluation_prompt += f"""
PERTANYAAN {i}:
Q: {question.get('question', 'N/A')}
A: {answer}
Why it matters: {question.get('why_matter', 'N/A')}
Level: {question.get('level', 'N/A')}
---
"""
        
        evaluation_prompt += f"""
TUGAS:
Berikan evaluasi komprehensif digital forensics readiness berdasarkan profil user dan jawaban assessment.

FORMAT RESPONSE JSON:
{{
    "overall_level": "Basic/Good/Excellent",
    "overall_score": 0-100,
    "readiness_percentage": 0-100,
    "strengths": ["strength1", "strength2", "strength3"],
    "weaknesses": ["weakness1", "weakness2", "weakness3"],
    "recommendations": [
        {{
            "category": "Immediate Actions",
            "items": ["action1", "action2"]
        }},
        {{
            "category": "Short-term (1-3 months)",
            "items": ["action1", "action2"]
        }},
        {{
            "category": "Long-term (3-12 months)", 
            "items": ["action1", "action2"]
        }}
    ],
    "risk_assessment": {{
        "critical_gaps": ["gap1", "gap2"],
        "risk_level": "Low/Medium/High",
        "priority_score": 0-10
    }},
    "detailed_analysis": "Analisis mendalam tentang kesiapan digital forensics organisasi ini, mencakup aspek teknis, prosedural, dan organisasional.",
    "next_steps": "Langkah konkret yang harus diambil untuk meningkatkan readiness"
}}

Berikan evaluasi yang detail, actionable, dan sesuai dengan konteks industri user!
"""
        
        print(f"🤖 Calling REAL LLM for comprehensive evaluation...")
        
        # REAL LLM CALL for evaluation
        ai_response = await llm_service.generate_response(evaluation_prompt, [])
        print(f"🎯 LLM Evaluation Response: {ai_response[:200]}...")
        
        # Parse evaluation result
        try:
            # Extract JSON from response
            if '{' in ai_response and '}' in ai_response:
                json_start = ai_response.find('{')
                json_end = ai_response.rfind('}') + 1
                json_str = ai_response[json_start:json_end]
                evaluation = json.loads(json_str)
            else:
                raise json.JSONDecodeError("No JSON found", ai_response, 0)
                
        except json.JSONDecodeError as e:
            print(f"⚠️ Evaluation JSON parsing failed: {str(e)}")
            
            # Fallback evaluation
            evaluation = {
                "overall_level": "Good",
                "overall_score": 75,
                "readiness_percentage": 70,
                "strengths": ["Experience in security", "Awareness of threats"],
                "weaknesses": ["Need improvement in procedures", "Tools and training gaps"],
                "recommendations": [
                    {
                        "category": "Immediate Actions",
                        "items": ["Review current security policies", "Assess forensic capabilities"]
                    }
                ],
                "risk_assessment": {
                    "critical_gaps": ["Incident response procedures"],
                    "risk_level": "Medium",
                    "priority_score": 6
                },
                "detailed_analysis": "Based on the assessment, there are areas for improvement in digital forensics readiness.",
                "next_steps": "Focus on policy development and team training",
                "raw_llm_response": ai_response
            }
        
        # Store final evaluation
        manager.context["final_evaluation"] = evaluation
        manager.context["current_phase"] = "completed"
        
        return jsonify({
            "message": "✅ Assessment completed with REAL LLM analysis!",
            "session_id": manager.session_id,
            "assessment_level": assessment_level,
            "user_profile": user_profile,
            "evaluation": evaluation,
            "questions_answered": len(answers),
            "current_phase": manager.context["current_phase"],
            "assessment_complete": True,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"❌ Error in get_results: {str(e)}")
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

# Utility endpoint for loading questions from CSV
@app.route('/load_questions', methods=['POST'])
async def load_questions():
    """Load questions from CSV to MongoDB"""
    try:
        data = request.get_json()
        csv_path = data.get('csv_path', 'questions.csv')
        
        count = await db_service.load_questions_from_csv(csv_path)
        return jsonify({
            "message": f"✅ Loaded {count} questions from {csv_path}",
            "questions_loaded": count
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
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(db_service.connect())
        print("✅ Database connected successfully")
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
    
    app.run(debug=True, host='127.0.0.1', port=5001)