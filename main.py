"""
DF Readiness AI Assessment System
Main FastAPI application entry point
"""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

# Import project modules
from api.routes import router
from config.settings import settings
from services.database_service import db_service
from utils.helpers import setup_logging

# Setup logging
logger = setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events
    """
    # Startup
    try:
        logger.info("🚀 Starting DF Readiness AI Assessment Service...")
        
        # Initialize database connection
        await db_service.connect()
        logger.info("✅ Database connection established")
        
        # Load questions from CSV if database is empty
        questions = await db_service.get_all_questions()
        if not questions:
            logger.info("📚 No questions found, attempting to load from CSV...")
            csv_path = Path("data/df_readiness_questions.csv")
            if csv_path.exists():
                try:
                    count = await db_service.load_questions_from_csv(str(csv_path))
                    logger.info(f"✅ Successfully loaded {count} questions from CSV")
                except Exception as e:
                    logger.error(f"⚠️  Failed to load questions from CSV: {str(e)}")
            else:
                logger.warning(f"⚠️  CSV file not found at {csv_path}")
        else:
            logger.info(f"📚 Found {len(questions)} questions already loaded in database")
        
        logger.info("🎉 DF Readiness AI Assessment Service started successfully!")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Startup error: {str(e)}")
        raise
    
    # Shutdown
    try:
        logger.info("🔄 Shutting down DF Readiness AI Assessment Service...")
        await db_service.disconnect()
        logger.info("👋 DF Readiness AI Assessment Service shut down gracefully")
    except Exception as e:
        logger.error(f"❌ Shutdown error: {str(e)}")

# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered Digital Forensics Readiness Assessment System with personalized learning paths",
    version=settings.VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# Security middleware
if not settings.DEBUG:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS
    )

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Custom exception handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions"""
    logger.error(f"HTTP {exc.status_code} error on {request.url}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "type": "http_error"
            }
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors"""
    logger.error(f"Validation error on {request.url}: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": {
                "code": 422,
                "message": "Request validation failed",
                "type": "validation_error",
                "details": exc.errors()
            }
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(f"Unexpected error on {request.url}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": 500,
                "message": "Internal server error" if not settings.DEBUG else str(exc),
                "type": "internal_error"
            }
        }
    )

# Middleware for request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests"""
    start_time = asyncio.get_event_loop().time()
    
    # Log request
    logger.info(f"📥 {request.method} {request.url}")
    
    # Process request
    response = await call_next(request)
    
    # Calculate processing time
    process_time = asyncio.get_event_loop().time() - start_time
    
    # Log response
    logger.info(f"📤 {request.method} {request.url} - {response.status_code} ({process_time:.3f}s)")
    
    # Add processing time to response headers
    response.headers["X-Process-Time"] = str(process_time)
    
    return response

# Health check endpoint (root level)
@app.get("/")
async def root():
    """Root endpoint with basic service information"""
    return {
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "running",
        "docs": "/docs" if settings.DEBUG else "disabled",
        "api_prefix": "/api/v1"
    }

@app.get("/health")
async def health_check():
    """Detailed health check endpoint"""
    try:
        # Check database connection
        db_status = await db_service.health_check()
        
        return {
            "service": settings.APP_NAME,
            "version": settings.VERSION,
            "status": "healthy",
            "timestamp": asyncio.get_event_loop().time(),
            "checks": {
                "database": "healthy" if db_status else "unhealthy",
                "api": "healthy"
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "service": settings.APP_NAME,
                "version": settings.VERSION,
                "status": "unhealthy",
                "error": str(e)
            }
        )

# Include API routes
app.include_router(router, prefix="/api/v1", tags=["DF Readiness API"])

def run_server():
    """Run the FastAPI server"""
    try:
        logger.info(f"🌟 Starting {settings.APP_NAME} v{settings.VERSION}")
        logger.info(f"🔧 Environment: {settings.ENVIRONMENT}")
        logger.info(f"🐛 Debug mode: {settings.DEBUG}")
        logger.info(f"🌐 Host: {settings.HOST}:{settings.PORT}")
        
        uvicorn.run(
            "main:app",
            host=settings.HOST,
            port=settings.PORT,
            reload=settings.DEBUG,
            log_level=settings.LOG_LEVEL.lower(),
            access_log=settings.DEBUG,
            reload_dirs=["./"] if settings.DEBUG else None,
            reload_excludes=["*.pyc", "*.pyo", "__pycache__"] if settings.DEBUG else None
        )
    except KeyboardInterrupt:
        logger.info("👋 Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Failed to start server: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_server()