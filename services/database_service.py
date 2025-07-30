# services/database_service.py
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional, List, Dict, Any
import pandas as pd
from datetime import datetime
from bson import ObjectId
import json
import logging

from config.settings import settings
from models.user_models import UserProfile, PersonalizationData
from models.assessment_models import AssessmentQuestion, AssessmentSession, UserAnswer
from utils.helpers import setup_logging

logger = setup_logging()

class DatabaseService:
    def __init__(self):
        self.client = None
        self.db = None
        self._connected = False
        
    @property
    def collection(self):
        """Get the questions collection"""
        if self.db is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self.db[settings.QUESTIONS_COLLECTION]
    
    @property
    def connected(self):
        """Check if database is connected"""
        return self._connected
        
    async def connect(self):
        """Connect to MongoDB"""
        try:
            self.client = AsyncIOMotorClient(settings.MONGODB_URI)
            self.db = self.client[settings.DATABASE_NAME]
            
            # Test the connection
            await self.client.admin.command('ping')
            self._connected = True
            print("Connected to MongoDB")
        except Exception as e:
            self._connected = False
            print(f"Failed to connect to MongoDB: {str(e)}")
            raise
        
    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            self._connected = False
            print("Disconnected from MongoDB")
    
    async def load_questions_from_csv(self, csv_path: str):
        """Load questions from CSV to MongoDB"""
        try:
            df = pd.read_csv(csv_path)
            questions = []
            
            for _, row in df.iterrows():
                question = {
                    "level": str(row['level']).strip(),
                    "question": str(row['question']).strip(),
                    "why_matter": str(row['why_matter']).strip(),
                    "created_at": datetime.utcnow()
                }
                questions.append(question)
            
            # Clear existing questions and insert new ones
            await self.collection.delete_many({})
            result = await self.collection.insert_many(questions)
            
            print(f"Loaded {len(result.inserted_ids)} questions from CSV")
            return len(result.inserted_ids)
            
        except Exception as e:
            print(f"Error loading questions from CSV: {str(e)}")
            return 0
    
    async def get_questions_by_level(self, level: str) -> List[Dict[str, Any]]:
        """Get questions filtered by level and return as dictionaries"""
        try:
            cursor = self.collection.find({"level": level})
            questions = []
            
            async for doc in cursor:
                # Convert ObjectId to string
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
                questions.append(doc)
                
            return questions
        except Exception as e:
            logger.error(f"Error getting questions by level: {str(e)}")
            return []
    
    async def get_all_questions(self) -> List[Dict[str, Any]]:
        """Get all questions as dictionaries"""
        try:
            cursor = self.collection.find({})
            questions = []
            
            async for doc in cursor:
                # Convert ObjectId to string
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
                questions.append(doc)
                
            return questions
        except Exception as e:
            logger.error(f"Error getting all questions: {str(e)}")
            return []
    
    async def count_questions(self) -> int:
        """Count total questions in database"""
        try:
            return await self.collection.count_documents({})
        except Exception as e:
            logger.error(f"Error counting questions: {str(e)}")
            return 0
    
    async def count_questions_by_level(self, level: str) -> int:
        """Count questions by level"""
        try:
            return await self.collection.count_documents({"level": level})
        except Exception as e:
            logger.error(f"Error counting questions by level: {str(e)}")
            return 0
    
    async def delete_all_questions(self) -> bool:
        """Delete all questions from database"""
        try:
            result = await self.collection.delete_many({})
            print(f"Deleted {result.deleted_count} questions")
            return True
        except Exception as e:
            logger.error(f"Error deleting questions: {str(e)}")
            return False
    
    async def save_user_profile(self, user_profile: UserProfile) -> str:
        """Save or update user profile"""
        try:
            user_dict = user_profile.dict(exclude={"id"})
            user_dict["updated_at"] = datetime.utcnow()
            
            # Check if user exists
            existing = await self.db[settings.USERS_COLLECTION].find_one(
                {"user_id": user_profile.user_id}
            )
            
            if existing:
                # Update existing user
                await self.db[settings.USERS_COLLECTION].update_one(
                    {"user_id": user_profile.user_id},
                    {"$set": user_dict}
                )
                return str(existing["_id"])
            else:
                # Create new user
                result = await self.db[settings.USERS_COLLECTION].insert_one(user_dict)
                return str(result.inserted_id)
                
        except Exception as e:
            print(f"Error saving user profile: {str(e)}")
            return None
    
    async def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """Get user profile by user_id"""
        try:
            doc = await self.db[settings.USERS_COLLECTION].find_one({"user_id": user_id})
            if doc:
                doc['_id'] = str(doc['_id'])
                return UserProfile(**doc)
            return None
        except Exception as e:
            print(f"Error getting user profile: {str(e)}")
            return None
    
    async def create_assessment_session(self, session: AssessmentSession) -> str:
        """Create new assessment session"""
        try:
            session_dict = session.dict(exclude={"id"})
            result = await self.db[settings.SESSIONS_COLLECTION].insert_one(session_dict)
            return str(result.inserted_id)
        except Exception as e:
            print(f"Error creating assessment session: {str(e)}")
            return None
    
    async def get_assessment_session(self, session_id: str) -> Optional[AssessmentSession]:
        """Get assessment session by session_id"""
        try:
            doc = await self.db[settings.SESSIONS_COLLECTION].find_one({"session_id": session_id})
            if doc:
                doc['_id'] = str(doc['_id'])
                return AssessmentSession(**doc)
            return None
        except Exception as e:
            print(f"Error getting assessment session: {str(e)}")
            return None
    
    async def update_assessment_session(self, session_id: str, update_data: Dict[str, Any]) -> bool:
        """Update assessment session"""
        try:
            update_data["updated_at"] = datetime.utcnow()
            result = await self.db[settings.SESSIONS_COLLECTION].update_one(
                {"session_id": session_id},
                {"$set": update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error updating assessment session: {str(e)}")
            return False
    
    async def add_answer_to_session(self, session_id: str, answer: UserAnswer) -> bool:
        """Add answer to assessment session"""
        try:
            answer_dict = answer.dict()
            result = await self.db[settings.SESSIONS_COLLECTION].update_one(
                {"session_id": session_id},
                {
                    "$push": {"answers": answer_dict},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error adding answer to session: {str(e)}")
            return False
    
    async def get_user_sessions(self, user_id: str) -> List[AssessmentSession]:
        """Get all sessions for a user"""
        try:
            cursor = self.db[settings.SESSIONS_COLLECTION].find(
                {"user_id": user_id}
            ).sort("started_at", -1)
            
            sessions = []
            async for doc in cursor:
                doc['_id'] = str(doc['_id'])
                sessions.append(AssessmentSession(**doc))
                
            return sessions
        except Exception as e:
            print(f"Error getting user sessions: {str(e)}")
            return []

# Global database service instance
db_service = DatabaseService()