"""
Main Flask Application
Digital Forensics Readiness Assessment API
"""
from flask import Flask, request, jsonify
from flask_cors import CORS

from config.settings import settings
from services.database_service import db_service
from api.auth.models import db as pg_db, User
from api.auth.jwt_utils import decode_token

# Import blueprints
from api.auth import auth_bp
from api.start_profiling import start_profiling_bp
from api.assessment_before import assessment_before_bp
from api.result import result
from api.rag_faiss import rag_faiss_bp
from api.v2.assessment_before import assessment_before_bp_v2 as assessment_before_bp_v2


# ============== APP INITIALIZATION ==============
app = Flask(__name__)
app.secret_key = settings.SECRET_KEY or 'secret_key'

# CORS configuration
CORS(app, supports_credentials=True)

# PostgreSQL configuration
app.config['SQLALCHEMY_DATABASE_URI'] = settings.POSTGRES_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
pg_db.init_app(app)


# ============== REGISTER BLUEPRINTS ==============
app.register_blueprint(auth_bp, url_prefix='/api/v1/auth')
app.register_blueprint(start_profiling_bp, url_prefix='/api/v1/start_profiling')
app.register_blueprint(assessment_before_bp, url_prefix='/api/v1/assessment_before')
app.register_blueprint(result, url_prefix='/api/v1/result')
app.register_blueprint(rag_faiss_bp, url_prefix='/api/v1/rag_faiss')
app.register_blueprint(assessment_before_bp_v2, url_prefix='/api/v2/assessment_before')


# ============== JWT MIDDLEWARE ==============
PUBLIC_PATHS = {
    '/',
    '/api/v1/auth/login',
    '/api/v1/auth/register',
    '/api/v1/auth/refresh'
}

@app.before_request
def jwt_protect_routes():
    """Protect all routes except public endpoints with JWT"""
    # Allow public endpoints
    if request.path in PUBLIC_PATHS or request.path.startswith('/static'):
        return
    
    # Skip OPTIONS for CORS preflight
    if request.method == 'OPTIONS':
        return
    
    # Check Authorization header
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.lower().startswith('bearer '):
        return jsonify({'error': 'Authorization header missing'}), 401
    
    # Extract and validate token
    token = auth_header.split(' ', 1)[1].strip()
    try:
        payload = decode_token(token)
        
        if payload.get('type') != 'access':
            return jsonify({'error': 'Invalid token type'}), 401
        
        user = User.query.get(payload.get('sub'))
        if not user:
            return jsonify({'error': 'User not found'}), 401
        
        # Attach user to request
        setattr(request, 'current_user', user)
        
    except Exception as e:
        return jsonify({'error': 'Invalid token', 'detail': str(e)}), 401


# ============== ROUTES ==============
@app.route('/', methods=['GET'])
def home():
    """API information"""
    return jsonify({
        "message": "Digital Forensics Readiness Assessment API",
        "version": "2.0",
        "features": [
            "Profiling",
            "FAISS Similarity Search",
            "Likert Scale Assessment",
            "LLM Evaluation"
        ]
    })


# ============== ERROR HANDLERS ==============
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


# ============== DATABASE INITIALIZATION ==============
async def initialize_database():
    """Initialize database connections and check data"""
    try:
        await db_service.connect()
        print("✓ Database connected successfully")
        
        question_count = await db_service.count_questions()
        keterangan_count = await db_service.count_keterangan()
        
        print(f"✓ Questions in database: {question_count}")
        print(f"✓ Keterangan in database: {keterangan_count}")
        
        if question_count == 0:
            print("⚠ Warning: No questions found in database")
        
        if keterangan_count == 0:
            print("⚠ Warning: No keterangan found in database")
        
    except Exception as e:
        print(f"✗ Database initialization failed: {str(e)}")
        raise


def initialize_postgres():
    """Initialize PostgreSQL tables and seed default user"""
    try:
        pg_db.create_all()
        print("✓ PostgreSQL tables created")
        
        # Seed default user if not exists
        if not User.query.filter(
            (User.username == "kingrokade") | (User.email == "kingrokade@example.com")
        ).first():
            default_user = User(
                username="kingrokade",
                email="kingrokade@example.com"
            )
            default_user.set_password("benteng88")
            pg_db.session.add(default_user)
            pg_db.session.commit()
            print("✓ Default user seeded: kingrokade / benteng88")
        else:
            print("✓ Default user already exists")
            
    except Exception as e:
        print(f"✗ PostgreSQL initialization failed: {e}")


# ============== APPLICATION STARTUP ==============
if __name__ == '__main__':
    print("=" * 50)
    print("Starting Digital Forensics Readiness API")
    print("=" * 50)
    
    # Initialize databases
    with app.app_context():
        initialize_postgres()
    
    # TODO: Initialize MongoDB connection if needed
    # import asyncio
    # asyncio.run(initialize_database())
    
    print("=" * 50)
    print("Server starting on http://0.0.0.0:5001")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5001)