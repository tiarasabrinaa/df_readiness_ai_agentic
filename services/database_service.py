          # services/database_service.py
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional, List, Dict, Any
import pandas as pd
from datetime import datetime
from bson import ObjectId
import json
import logging
import random

# Import settings properly
try:
    from config.settings import settings
except ImportError:
    # Fallback settings if config module not found
    class FallbackSettings:
        MONGODB_URI = "mongodb://localhost:27017"
        DATABASE_NAME = "df_readiness"
        QUESTIONS_COLLECTION = "questions"
        USERS_COLLECTION = "users"
        SESSIONS_COLLECTION = "sessions"
    
    settings = FallbackSettings()

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
            logger.info(f"✅ Connected to MongoDB: {settings.DATABASE_NAME}")
            
            # Show collections info
            collections = await self.db.list_collection_names()
            logger.info(f"Available collections: {collections}")
            
        except Exception as e:
            self._connected = False
            logger.error(f"❌ Failed to connect to MongoDB: {str(e)}")
            raise
        
    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            self._connected = False
            logger.info("Disconnected from MongoDB")
    
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
            
            logger.info(f"Loaded {len(result.inserted_ids)} questions from CSV")
            return len(result.inserted_ids)
            
        except Exception as e:
            logger.error(f"Error loading questions from CSV: {str(e)}")
            return 0
    
    async def get_questions_by_level(self, level: str, limit: int = None) -> List[Dict[str, Any]]:
        """Get questions filtered by level and return as dictionaries"""
        try:
            # Create query
            query = {"level": level}
            cursor = self.collection.find(query)
            
            # Apply limit if specified
            if limit:
                cursor = cursor.limit(limit)
            
            questions = []
            async for doc in cursor:
                # Convert ObjectId to string for JSON serialization
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
                questions.append(doc)
            
            logger.info(f"Retrieved {len(questions)} questions for level: {level}")
            return questions
            
        except Exception as e:
            logger.error(f"Error getting questions by level {level}: {str(e)}")
            return []
    
    async def get_random_questions_by_level(self, level: str, count: int = 3) -> List[Dict[str, Any]]:
        """Get random questions by level using MongoDB aggregation"""
        try:
            pipeline = [
                {"$match": {"level": level}},
                {"$sample": {"size": count}}
            ]
            
            questions = []
            async for doc in self.collection.aggregate(pipeline):
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
                questions.append(doc)
            
            logger.info(f"Retrieved {len(questions)} random questions for level: {level}")
            return questions
            
        except Exception as e:
            logger.error(f"Error getting random questions by level {level}: {str(e)}")
            # Fallback to regular query
            all_questions = await self.get_questions_by_level(level)
            if all_questions and len(all_questions) > count:
                return random.sample(all_questions, count)
            return all_questions
    
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
            
            logger.info(f"Retrieved {len(questions)} total questions")
            return questions
            
        except Exception as e:
            logger.error(f"Error getting all questions: {str(e)}")
            return []
    
    async def count_questions(self) -> int:
        """Count total questions in database"""
        try:
            count = await self.collection.count_documents({})
            return count
        except Exception as e:
            logger.error(f"Error counting questions: {str(e)}")
            return 0
    
    async def count_questions_by_level(self, level: str) -> int:
        """Count questions by level"""
        try:
            count = await self.collection.count_documents({"level": level})
            return count
        except Exception as e:
            logger.error(f"Error counting questions by level {level}: {str(e)}")
            return 0
    
    async def get_level_distribution(self) -> Dict[str, int]:
        """Get distribution of questions by level"""
        try:
            pipeline = [
                {"$group": {"_id": "$level", "count": {"$sum": 1}}},
                {"$sort": {"_id": 1}}
            ]
            
            distribution = {}
            async for doc in self.collection.aggregate(pipeline):
                distribution[doc["_id"]] = doc["count"]
            
            return distribution
            
        except Exception as e:
            logger.error(f"Error getting level distribution: {str(e)}")
            return {}
    
    async def insert_question(self, level: str, question: str, why_matter: str) -> str:
        """Insert a single question"""
        try:
            doc = {
                "level": level.strip(),
                "question": question.strip(),
                "why_matter": why_matter.strip(),
                "created_at": datetime.utcnow()
            }
            
            result = await self.collection.insert_one(doc)
            logger.info(f"Inserted question with ID: {result.inserted_id}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Error inserting question: {str(e)}")
            return None
    
    async def insert_questions_batch(self, questions: List[Dict[str, str]]) -> int:
        """Insert multiple questions at once"""
        try:
            # Add timestamps to all questions
            for question in questions:
                question["created_at"] = datetime.utcnow()
            
            result = await self.collection.insert_many(questions)
            logger.info(f"Inserted {len(result.inserted_ids)} questions")
            return len(result.inserted_ids)
            
        except Exception as e:
            logger.error(f"Error inserting questions batch: {str(e)}")
            return 0
    
    async def delete_all_questions(self) -> bool:
        """Delete all questions from database"""
        try:
            result = await self.collection.delete_many({})
            logger.info(f"Deleted {result.deleted_count} questions")
            return True
        except Exception as e:
            logger.error(f"Error deleting questions: {str(e)}")
            return False
    
    async def delete_questions_by_level(self, level: str) -> int:
        """Delete questions by level"""
        try:
            result = await self.collection.delete_many({"level": level})
            logger.info(f"Deleted {result.deleted_count} questions for level: {level}")
            return result.deleted_count
        except Exception as e:
            logger.error(f"Error deleting questions by level {level}: {str(e)}")
            return 0
    
    async def update_question(self, question_id: str, updates: Dict[str, Any]) -> bool:
        """Update a specific question"""
        try:
            updates["updated_at"] = datetime.utcnow()
            result = await self.collection.update_one(
                {"_id": ObjectId(question_id)},
                {"$set": updates}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating question {question_id}: {str(e)}")
            return False
    
    # User and Session related methods (keeping from original)
    async def save_user_profile(self, user_profile: dict) -> str:
        """Save or update user profile"""
        try:
            user_profile["updated_at"] = datetime.utcnow()
            
            # Check if user exists
            user_id = user_profile.get("user_id")
            if not user_id:
                return None
                
            existing = await self.db[settings.USERS_COLLECTION].find_one(
                {"user_id": user_id}
            )
            
            if existing:
                # Update existing user
                await self.db[settings.USERS_COLLECTION].update_one(
                    {"user_id": user_id},
                    {"$set": user_profile}
                )
                return str(existing["_id"])
            else:
                # Create new user
                result = await self.db[settings.USERS_COLLECTION].insert_one(user_profile)
                return str(result.inserted_id)
                
        except Exception as e:
            logger.error(f"Error saving user profile: {str(e)}")
            return None
    
    async def get_user_profile(self, user_id: str) -> Optional[dict]:
        """Get user profile by user_id"""
        try:
            doc = await self.db[settings.USERS_COLLECTION].find_one({"user_id": user_id})
            if doc:
                doc['_id'] = str(doc['_id'])
                return doc
            return None
        except Exception as e:
            logger.error(f"Error getting user profile: {str(e)}")
            return None
    
    async def create_assessment_session(self, session_data: dict) -> str:
        """Create new assessment session"""
        try:
            session_data["created_at"] = datetime.utcnow()
            session_data["updated_at"] = datetime.utcnow()
            
            result = await self.db[settings.SESSIONS_COLLECTION].insert_one(session_data)
            logger.info(f"Created assessment session: {result.inserted_id}")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error creating assessment session: {str(e)}")
            return None
    
    async def get_assessment_session(self, session_id: str) -> Optional[dict]:
        """Get assessment session by session_id"""
        try:
            doc = await self.db[settings.SESSIONS_COLLECTION].find_one({"session_id": session_id})
            if doc:
                doc['_id'] = str(doc['_id'])
                return doc
            return None
        except Exception as e:
            logger.error(f"Error getting assessment session: {str(e)}")
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
            logger.error(f"Error updating assessment session: {str(e)}")
            return False
    
    async def get_user_sessions(self, user_id: str) -> List[dict]:
        """Get all sessions for a user"""
        try:
            cursor = self.db[settings.SESSIONS_COLLECTION].find(
                {"user_id": user_id}
            ).sort("created_at", -1)
            
            sessions = []
            async for doc in cursor:
                doc['_id'] = str(doc['_id'])
                sessions.append(doc)
                
            return sessions
        except Exception as e:
            logger.error(f"Error getting user sessions: {str(e)}")
            return []
    
    # Health check methods
    async def health_check(self) -> Dict[str, Any]:
        """Perform database health check"""
        try:
            # Test connection
            await self.client.admin.command('ping')
            
            # Get stats
            total_questions = await self.count_questions()
            level_distribution = await self.get_level_distribution()
            
            return {
                "status": "healthy",
                "connected": True,
                "database": settings.DATABASE_NAME,
                "total_questions": total_questions,
                "level_distribution": level_distribution,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "status": "unhealthy", 
                "connected": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

# Global database service instance
db_service = DatabaseService()