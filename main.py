from flask import Flask, request, jsonify, session
from flask_cors import CORS
import uuid
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List
from functools import wraps

# REAL imports - ganti path sesuai struktur project lu
from services.database_service import db_service
from services.llm_service import llm_service

app = Flask(__name__)
app.secret_key = 'your_secret_key_change_this_in_production'
CORS(app, supports_credentials=True)

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
def startup():
    """Connect to database on startup"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def _startup():
        try:
            await db_service.connect()
            print("✅ Database connected successfully")
            
            # Load questions if needed
            question_count = await db_service.count_questions()
            print(f"📊 Total questions in database: {question_count}")
            
            if question_count == 0:
                print("⚠️ No questions found in database. You may need to load questions.")
            else:
                # Show questions by level
                for level in ["basic", "intermediate", "advanced"]:
                    count = await db_service.count_questions_by_level(level)
                    print(f"   - {level}: {count} questions")
            
        except Exception as e:
            print(f"❌ Failed to initialize database: {str(e)}")
    
    try:
        loop.run_until_complete(_startup())
    finally:
        loop.close()

@app.route('/', methods=['GET'])
def home():
    """API information"""
    return jsonify({
        "message": "🚀 REAL Cybersecurity Readiness Assessment API with LLM",
        "version": "2.1-DATABASE",
        "flow": {
            "1": "GET /start_profiling - Get 5 profiling questions from AI",
            "2": "POST /submit_answers - Submit answers in JSON format, REAL LLM determines level", 
            "3": "GET /get_test_questions - Get 3 questions from REAL MongoDB",
            "4": "POST /submit_test_answers - Submit test answers",
            "5": "GET /get_results - REAL LLM evaluation and recommendations"
        },
        "features": {
            "llm_integration": "✅ Real Telkom LLM API",
            "database": "✅ Real MongoDB with Motor - Questions from DB",
            "personalization": "✅ AI-powered level assessment",
            "evaluation": "✅ Comprehensive AI analysis"
        }
    })

@app.route('/start_profiling', methods=['GET'])
@async_route
async def start_profiling():
    """Generate 5 profiling questions using AI"""
    try:
        manager = get_or_create_session()
        
        # Use AI to generate contextual profiling questions
        profiling_prompt = """
Kamu adalah AI expert dalam cybersecurity assessment. Generate 5 pertanyaan profiling yang akan membantu menentukan level assessment yang tepat untuk user.

Pertanyaan harus mencakup:
1. Industri/bidang usaha
2. Ukuran organisasi 
3. Posisi/role user
4. Pengalaman cybersecurity
5. Riwayat insiden keamanan

FORMAT RESPONSE JSON:
{
    "questions": [
        "Pertanyaan 1 tentang industri...",
        "Pertanyaan 2 tentang ukuran perusahaan...", 
        "Pertanyaan 3 tentang posisi/role...",
        "Pertanyaan 4 tentang pengalaman...",
        "Pertanyaan 5 tentang riwayat insiden..."
    ]
}

Buatlah pertanyaan yang spesifik dan akan menghasilkan informasi yang berguna untuk assessment level.
"""
        
        print(f"🤖 Generating profiling questions using AI...")
        ai_response = await llm_service.generate_response(profiling_prompt, [])
        
        # Parse AI response
        try:
            if '{' in ai_response and '}' in ai_response:
                json_start = ai_response.find('{')
                json_end = ai_response.rfind('}') + 1
                json_str = ai_response[json_start:json_end]
                ai_result = json.loads(json_str)
                questions = ai_result.get("questions", [])
            else:
                raise json.JSONDecodeError("No JSON found", ai_response, 0)
        except json.JSONDecodeError:
            print(f"⚠️ Using fallback questions due to AI parsing error")
            # Fallback questions
            questions = [
                "Apa jenis industri atau bidang usaha yang Anda geluti?",
                "Berapa jumlah karyawan di organisasi Anda?", 
                "Apa posisi/jabatan Anda saat ini di perusahaan?",
                "Berapa tahun pengalaman Anda dalam bidang keamanan IT/cybersecurity?",
                "Apakah organisasi Anda pernah mengalami insiden keamanan? Jelaskan singkat."
            ]
        
        return jsonify({
            "session_id": manager.session_id,
            "questions": questions,
            "total_questions": len(questions),
            "current_phase": manager.context["current_phase"],
            "instruction": "Jawab semua pertanyaan dengan detail untuk analisis LLM yang akurat",
            "expected_format": "JSON dengan format: {'question1': 'answer1', 'question2': 'answer2', ...}"
        })
        
    except Exception as e:
        print(f"❌ Error in start_profiling: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/submit_answers', methods=['POST'])
@async_route
async def submit_answers():
    """Process profiling answers in JSON format and determine assessment level using REAL LLM"""
    try:
        manager = get_or_create_session()
        
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
        
        data = request.get_json()
        
        # Accept both formats: array of answers or question-answer pairs
        if 'answers' in data and isinstance(data['answers'], list):
            # Legacy format: array of answers
            answers = data.get('answers', [])
            if len(answers) != 5:
                return jsonify({"error": "Please provide exactly 5 answers."}), 400
            
            # Convert to question-answer format
            question_keys = ["industry", "company_size", "position", "experience", "security_incidents"]
            qa_pairs = {}
            for idx, answer in enumerate(answers):
                if idx < len(question_keys):
                    qa_pairs[f"question{idx+1}"] = answer
                    manager.update_profile_data(question_keys[idx], answer)
        
        elif any(key.startswith('question') for key in data.keys()):
            # New format: question-answer pairs
            qa_pairs = {k: v for k, v in data.items() if k.startswith('question')}
            
            if len(qa_pairs) != 5:
                return jsonify({"error": "Please provide exactly 5 question-answer pairs."}), 400
            
            # Store profile data
            question_keys = ["industry", "company_size", "position", "experience", "security_incidents"]
            for idx, (question, answer) in enumerate(qa_pairs.items()):
                if idx < len(question_keys):
                    manager.update_profile_data(question_keys[idx], answer)
        else:
            return jsonify({
                "error": "Invalid format. Please provide either 'answers' array or 'question1', 'question2', etc. keys"
            }), 400
        
        # Prepare REAL prompt for LLM analysis
        profiling_prompt = f"""
Kamu adalah AI expert dalam cybersecurity assessment. Berdasarkan profiling data user berikut, tentukan level assessment yang tepat:

PROFILING DATA (JSON format):
{json.dumps(qa_pairs, indent=2, ensure_ascii=False)}

TUGAS:
Analisis profile user dan tentukan level assessment yang tepat berdasarkan kriteria:

basic:
- Pengalaman < 2 tahun dalam cybersecurity
- Perusahaan kecil (<50 karyawan) atau tidak ada dedicated security team
- Belum pernah/jarang mengalami insiden serius
- Role tidak spesifik ke security (general IT, admin, dll)

intermediate:
- Pengalaman 2-7 tahun dalam cybersecurity  
- Perusahaan menengah (50-500 karyawan) dengan basic security measures
- Pernah mengalami beberapa insiden dan ada proses handling
- Role terkait security tapi belum senior level

advanced:
- Pengalaman >7 tahun atau role senior security
- Perusahaan besar (>500 karyawan) dengan mature security program
- Pengalaman menangani insiden kompleks/APT
- Role seperti CISO, Senior Security Analyst, Security Architect

FORMAT RESPONSE JSON:
{{
    "assessment_level": "basic/intermediate/advanced",
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
                
            assessment_level = llm_result.get("assessment_level", "basic")
            
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON parsing failed: {str(e)}")
            print(f"Raw LLM response: {ai_response}")
            
            # Fallback: extract level from text
            ai_lower = ai_response.lower()
            if "advanced" in ai_lower:
                assessment_level = "advanced"
            elif "intermediate" in ai_lower:
                assessment_level = "intermediate"
            else:
                assessment_level = "basic"
                
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
        manager.context["profiling_qa_pairs"] = qa_pairs
        
        return jsonify({
            "message": "✅ Profiling complete. Level determined by REAL LLM analysis.",
            "session_id": manager.session_id,
            "profile_data": manager.context["user_profile"],
            "qa_pairs": qa_pairs,
            "assessment_level": assessment_level,
            "llm_analysis": llm_result,
            "current_phase": manager.context["current_phase"],
            "next_step": "Call GET /get_test_questions to get questions from MongoDB"
        })
        
    except Exception as e:
        print(f"❌ Error in submit_answers: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/get_test_questions', methods=['GET'])
@async_route
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
            for fallback_level in ["intermediate", "basic", "advanced"]:
                if fallback_level != assessment_level:
                    questions = await db_service.get_questions_by_level(fallback_level)
                    if questions:
                        print(f"✅ Found {len(questions)} questions from {fallback_level} level")
                        assessment_level = fallback_level  # Update level for response
                        break
        
        if not questions:
            return jsonify({
                "error": "No questions available in database",
                "suggestion": "Please load questions using database seeding or manual insertion",
                "available_endpoints": ["/db_stats", "/seed_questions"]
            }), 404
        
        # Take only 3 questions randomly
        import random
        if len(questions) > 3:
            selected_questions = random.sample(questions, 3)
        else:
            selected_questions = questions
        
        # Store questions in session
        manager.context["test_questions"] = selected_questions
        manager.context["current_phase"] = "testing"
        
        return jsonify({
            "session_id": manager.session_id,
            "assessment_level": assessment_level,
            "questions": selected_questions,
            "total_questions": len(selected_questions),
            "current_phase": manager.context["current_phase"],
            "instruction": "Jawab semua pertanyaan dengan detail untuk evaluasi LLM yang komprehensif",
            "expected_format": "Array of answers: ['answer1', 'answer2', 'answer3']"
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
        if not all(str(answer).strip() for answer in answers):
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
@async_route
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
        qa_pairs = manager.context.get("profiling_qa_pairs", {})
        
        # Prepare comprehensive evaluation prompt
        evaluation_prompt = f"""
Kamu adalah expert dalam cybersecurity dan digital forensics readiness assessment. 

USER PROFILE SUMMARY:
- Industri: {user_profile.get('industry', 'Unknown')}
- Ukuran perusahaan: {user_profile.get('company_size', 'Unknown')}
- Posisi: {user_profile.get('position', 'Unknown')}
- Pengalaman: {user_profile.get('experience', 'Unknown')}
- Assessment Level: {assessment_level}

PROFILING Q&A:
{json.dumps(qa_pairs, indent=2, ensure_ascii=False)}

ASSESSMENT TEST RESULTS:
"""
        
        # Add Q&A pairs from database questions
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
    "overall_level": "basic/intermediate/advanced",
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
            "profiling_qa": qa_pairs,
            "test_questions": len(questions),
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

# Database utility endpoints
@app.route('/db_stats', methods=['GET'])
@async_route
async def db_stats():
    """Get database statistics"""
    try:
        total_questions = await db_service.count_questions()
        
        stats = {
            "total_questions": total_questions,
            "questions_by_level": {}
        }
        
        for level in ["basic", "intermediate", "advanced"]:
            count = await db_service.count_questions_by_level(level)
            stats["questions_by_level"][level] = count
        
        return jsonify({
            "message": "Database statistics", 
            "stats": stats,
            "database_connected": db_service.connected
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/seed_questions', methods=['POST'])
@async_route
async def seed_questions():
    """Seed database with sample questions"""
    try:
        sample_questions = [
            {
                "level": "basic",
                "question": "Does your organization have a documented disaster recovery strategy?",
                "why_matter": "Having a documented disaster recovery strategy is essential for ensuring organizational continuity in case of a disaster."
            },
            {
                "level": "basic", 
                "question": "Are regular backups performed and tested in your organization?",
                "why_matter": "Regular and tested backups are crucial for data recovery and business continuity."
            },
            {
                "level": "intermediate",
                "question": "Does your organization have an incident response team with defined roles and responsibilities?",
                "why_matter": "A well-defined incident response team ensures quick and effective response to security incidents."
            },
            {
                "level": "intermediate",
                "question": "Are forensic tools and technologies regularly updated and tested?",
                "why_matter": "Updated forensic tools ensure effective evidence collection and analysis."
            },
            {
                "level": "advanced",
                "question": "Does your organization conduct regular threat hunting activities?",
                "why_matter": "Proactive threat hunting helps identify advanced persistent threats before they cause damage."
            },
            {
                "level": "advanced",
                "question": "Are forensic procedures integrated with legal and compliance requirements?",
                "why_matter": "Integration with legal requirements ensures forensic evidence is admissible in court."
            }
        ]
        
        # Insert sample questions
        collection = db_service.collection
        await collection.delete_many({})  # Clear existing
        
        for question in sample_questions:
            question["created_at"] = datetime.utcnow()
        
        result = await collection.insert_many(sample_questions)
        
        return jsonify({
            "message": f"✅ Seeded {len(result.inserted_ids)} sample questions",
            "questions_inserted": len(result.inserted_ids)
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
        print(f"❌ Startup failed: {str(e)}")
    
    app.run(debug=True, host='127.0.0.1', port=5001)