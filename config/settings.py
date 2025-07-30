import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    APP_NAME: str = "DF Readiness AI Assessment"
    VERSION: str = "0.1.0"
    DEBUG: bool = True
    ALLOWED_HOSTS: list = ["*"]
    CORS_ORIGINS: list = ["*"]
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    HOST: str = os.getenv("HOST", "0.0.0.0")  # <-- Tambahkan baris ini
    PORT: int = int(os.getenv("PORT", 8000))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # LLM Config
    LLM_URL = os.getenv("URL_CUSTOM_LLM_APILOGY")
    LLM_TOKEN = os.getenv("TOKEN_CUSTOM_LLM_APILOGY")
    
    # Database Config
    MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "df_readiness_db")
    
    # Collections
    USERS_COLLECTION = "users"
    ASSESSMENTS_COLLECTION = "assessments"
    QUESTIONS_COLLECTION = "questions"
    SESSIONS_COLLECTION = "sessions"

settings = Settings()