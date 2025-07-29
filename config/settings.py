import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
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