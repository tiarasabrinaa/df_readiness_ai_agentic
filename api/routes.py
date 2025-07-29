# api/routes.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional
import uuid

from services.database_service import db_service
from agents.personalization_agent import personalization_agent
from agents.assessment_agent import assessment_agent

router = APIRouter()

# Request/Response Models
class PersonalizationRequest(BaseModel):
    user_id: str
    user_input: str
    session_id: Optional[str] = None

class AssessmentStartRequest(BaseModel):
    user_id: str

class AssessmentAnswerRequest(BaseModel):
    session_id: str
    question_id: str
    user_answer: str

class HealthResponse(BaseModel):
    status: str
    message: str

# Routes
@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(status="healthy", message="DF Readiness AI Service is running")

@router.post("/personalization/start")
async def start_personalization(request: PersonalizationRequest):
    """
    Start or continue personalization process
    """
    try:
        # Reset agent for new session if no session_id provided
        if not request.session_id:
            personalization_agent.reset_session()
        
        result = await personalization_agent.process_user_input(
            user_id=request.user_id,
            user_input=request.user_input,
            session_id=request.session_id
        )
        
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Personalization error: {str(e)}")

@router.post("/assessment/start")
async def start_assessment(request: AssessmentStartRequest):
    """
    Start new assessment session
    """
    try:
        result = await assessment_agent.start_assessment(request.user_id)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Assessment start error: {str(e)}")

@router.post("/assessment/answer")
async def submit_answer(request: AssessmentAnswerRequest):
    """
    Submit answer and get next question or results
    """
    try:
        result = await assessment_agent.process_answer(
            session_id=request.session_id,
            user_answer=request.user_answer,
            question_id=request.question_id
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Answer processing error: {str(e)}")

@router.get("/user/{user_id}/profile")
async def get_user_profile(user_id: str):
    """
    Get user profile and personalization data
    """
    try:
        profile = await db_service.get_user_profile(user_id)
        
        if not profile:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        return {
            "success": True,
            "data": profile.dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Profile retrieval error: {str(e)}")

@router.get("/user/{user_id}/sessions")
async def get_user_sessions(user_id: str):
    """
    Get all assessment sessions for a user
    """
    try:
        sessions = await db_service.get_user_sessions(user_id)
        
        return {
            "success": True,
            "data": [session.dict() for session in sessions]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sessions retrieval error: {str(e)}")

@router.get("/assessment/{session_id}/results")
async def get_assessment_results(session_id: str):
    """
    Get detailed assessment results
    """
    try:
        session = await db_service.get_assessment_session(session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="Assessment session not found")
        
        if session.status != "completed":
            raise HTTPException(status_code=400, detail="Assessment not yet completed")
        
        return {
            "success": True,
            "data": {
                "session_id": session_id,
                "status": session.status,
                "results": session.assessment_result,
                "total_questions": len(session.answers),
                "started_at": session.started_at,
                "completed_at": session.completed_at,
                "answers": [answer.dict() for answer in session.answers]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Results retrieval error: {str(e)}")

@router.post("/admin/load-questions")
async def load_questions_from_csv():
    """
    Admin endpoint to load questions from CSV file
    """
    try:
        csv_path = "data/df_readiness_questions.csv"
        count = await db_service.load_questions_from_csv(csv_path)
        
        return {
            "success": True,
            "message": f"Successfully loaded {count} questions from CSV"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CSV loading error: {str(e)}")

@router.get("/questions")
async def get_all_questions():
    """
    Get all available questions (for admin/debugging)
    """
    try:
        questions = await db_service.get_all_questions()
        
        return {
            "success": True,
            "data": [question.dict() for question in questions],
            "total": len(questions)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Questions retrieval error: {str(e)}")

# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio

from api.routes import router
from services.database_service import db_service

app = FastAPI(
    title="DF Readiness AI Assessment",
    description="AI-powered Digital Forensics Readiness Assessment System",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router, prefix="/api/v1")

@app.on_event("startup")
async def startup_event():
    """Initialize database connection and load initial data"""
    try:
        await db_service.connect()
        print("🚀 DF Readiness AI Assessment Service started successfully!")
        
        # Load questions from CSV if needed
        questions = await db_service.get_all_questions()
        if not questions:
            print("📚 No questions found, attempting to load from CSV...")
            csv_path = "data/df_readiness_questions.csv"
            try:
                count = await db_service.load_questions_from_csv(csv_path)
                print(f"✅ Loaded {count} questions from CSV")
            except Exception as e:
                print(f"⚠️  Could not load questions from CSV: {str(e)}")
        else:
            print(f"📚 {len(questions)} questions already loaded in database")
            
    except Exception as e:
        print(f"❌ Startup error: {str(e)}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup database connection"""
    await db_service.disconnect()
    print("👋 DF Readiness AI Assessment Service shut down")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )