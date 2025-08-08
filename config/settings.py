import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:
    # Application Info
    APP_NAME: str = "DF Readiness AI Assessment"
    VERSION: str = "2.1.0"
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    
    # Server Configuration
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", 5001))
    
    # CORS and Security
    ALLOWED_HOSTS: list = ["*"]
    CORS_ORIGINS: list = ["*"]
    SECRET_KEY: str = os.getenv("SECRET_KEY", "secret_key")
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # LLM Configuration
    LLM_URL: str = os.getenv("URL_CUSTOM_LLM_APILOGY", "")
    LLM_TOKEN: str = os.getenv("TOKEN_CUSTOM_LLM_APILOGY", "")
    
    # Validate LLM configuration
    if not LLM_URL or not LLM_TOKEN:
        print("⚠️ Warning: LLM configuration not complete. Check environment variables:")
        print("   - URL_CUSTOM_LLM_APILOGY")
        print("   - TOKEN_CUSTOM_LLM_APILOGY")
    
    # Database Configuration
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "df_readiness")
    
    # Mail Resend API Key
    MAIL_RESEND_API_KEY: str = os.getenv("MAIL_RESEND_API_KEY", "")

    # Collection Names
    USERS_COLLECTION: str = "users"
    ASSESSMENTS_COLLECTION: str = "assessments"
    QUESTIONS_COLLECTION: str = "questions"
    SESSIONS_COLLECTION: str = "sessions"
    
    # Assessment Configuration
    DEFAULT_PROFILING_QUESTIONS: int = 5
    DEFAULT_TEST_QUESTIONS: int = 3
    SUPPORTED_LEVELS: list = ["Beginner", "Intermediate", "Advanced"]
    
    # Session Configuration
    SESSION_TIMEOUT_HOURS: int = 24
    MAX_SESSIONS_PER_USER: int = 10
    
    # Validation settings
    MIN_ANSWER_LENGTH: int = 10
    MAX_ANSWER_LENGTH: int = 1000
    
    def __post_init__(self):
        """Validate settings after initialization"""
        if self.ENVIRONMENT == "production":
            if self.SECRET_KEY == "secret_key":
                raise ValueError("Please set a secure SECRET_KEY for production!")
            
            if not self.LLM_URL or not self.LLM_TOKEN:
                raise ValueError("LLM configuration is required for production!")
    
    def get_mongodb_config(self) -> dict:
        """Get MongoDB configuration as dictionary"""
        return {
            "uri": self.MONGODB_URI,
            "database": self.DATABASE_NAME,
            "collections": {
                "users": self.USERS_COLLECTION,
                "assessments": self.ASSESSMENTS_COLLECTION,
                "questions": self.QUESTIONS_COLLECTION,
                "sessions": self.SESSIONS_COLLECTION
            }
        }
    
    def get_llm_config(self) -> dict:
        """Get LLM configuration as dictionary"""
        return {
            "url": self.LLM_URL,
            "token": self.LLM_TOKEN,
            "timeout": 30,  # seconds
            "max_retries": 3
        }
    
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.ENVIRONMENT.lower() == "development"
    
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.ENVIRONMENT.lower() == "production"
    
    def print_config_summary(self):
        """Print configuration summary (safe for logging)"""
        print(f"""
🔧 Configuration Summary:
   App: {self.APP_NAME} v{self.VERSION}
   Environment: {self.ENVIRONMENT}
   Host: {self.HOST}:{self.PORT}
   Debug: {self.DEBUG}
   
   Database: {self.DATABASE_NAME}
   MongoDB: {self.MONGODB_URI.split('@')[-1] if '@' in self.MONGODB_URI else self.MONGODB_URI}
   
   LLM: {'✅ Configured' if self.LLM_URL and self.LLM_TOKEN else '❌ Not configured'}
   
   Assessment:
   - Profiling questions: {self.DEFAULT_PROFILING_QUESTIONS}
   - Test questions: {self.DEFAULT_TEST_QUESTIONS}
   - Supported levels: {', '.join(self.SUPPORTED_LEVELS)}
""")

# Create global settings instance
settings = Settings()

# Print config on import (only in development)
if settings.is_development():
    settings.print_config_summary()