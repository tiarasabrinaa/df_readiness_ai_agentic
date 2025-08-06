import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from typing import List, Dict, Any, Optional
import os
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

class DatabaseService:
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None
        self.questions_collection = None
        self.connection_string = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
        self.database_name = os.getenv('DATABASE_NAME', 'cybersecurity_assessment')
        self.collection_name = os.getenv('COLLECTION_NAME', 'questions')
    
    async def connect(self):
        """Connect to MongoDB database"""
        try:
            if self.client is not None:
                await self.disconnect()
            
            self.client = AsyncIOMotorClient(self.connection_string, serverSelectionTimeoutMS=5000)
            
            # Test the connection
            await self.client.admin.command('ping')
            
            self.db = self.client[self.database_name]
            self.questions_collection = self.db[self.collection_name]
            
            print(f"Successfully connected to MongoDB: {self.database_name}.{self.collection_name}")
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            print(f"Failed to connect to MongoDB: {str(e)}")
            raise Exception(f"Database connection failed: {str(e)}")
        except Exception as e:
            print(f"Unexpected error connecting to MongoDB: {str(e)}")
            raise Exception(f"Database connection error: {str(e)}")
    
    async def disconnect(self):
        """Disconnect from MongoDB database"""
        if self.client is not None:
            self.client.close()
            self.client = None
            self.db = None
            self.questions_collection = None
            print("Disconnected from MongoDB")
    
    def _ensure_connection(self):
        """Ensure database connection exists"""
        if self.client is None or self.db is None or self.questions_collection is None:
            raise Exception("Database not connected. Call connect() first.")
    
    async def count_questions(self) -> int:
        """Count total questions in database"""
        try:
            self._ensure_connection()
            count = await self.questions_collection.count_documents({})
            return count
        except Exception as e:
            print(f"Error counting questions: {str(e)}")
            return 0
    
    async def count_questions_by_level(self, level: str) -> int:
        """Count questions by DMAIC-S level"""
        try:
            self._ensure_connection()
            count = await self.questions_collection.count_documents({"category": level})
            return count
        except Exception as e:
            print(f"Error counting questions for level {level}: {str(e)}")
            return 0
    
    async def get_questions_by_level(self, level: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get questions by category level"""
        try:
            self._ensure_connection()

            query = {"category": level}

            projection = {
                "qualification": 1,
                "why": 1,
                "question": 1
            }

            # Execute query
            if limit is not None:
                cursor = self.questions_collection.find(query, projection).limit(limit)
            else:
                cursor = self.questions_collection.find(query, projection)
            
            # Convert cursor to list
            questions = []
            async for question in cursor:
                # Convert ObjectId to string for JSON serialization
                if '_id' in question:
                    question['_id'] = str(question['_id'])
                questions.append(question)
            
            print(f"Retrieved {len(questions)} questions for level: {level}")
            return questions
            
        except Exception as e:
            print(f"Error getting questions for level {level}: {str(e)}")
            return []

    
    async def get_all_questions(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get all questions from database"""
        try:
            self._ensure_connection()
            
            # Execute query
            if limit is not None:
                cursor = self.questions_collection.find({}).limit(limit)
            else:
                cursor = self.questions_collection.find({})
            
            # Convert cursor to list
            questions = []
            async for question in cursor:
                # Convert ObjectId to string for JSON serialization
                if '_id' in question:
                    question['_id'] = str(question['_id'])
                questions.append(question)
            
            print(f"Retrieved {len(questions)} total questions")
            return questions
            
        except Exception as e:
            print(f"Error getting all questions: {str(e)}")
            return []
    
    async def insert_question(self, question: Dict[str, Any]) -> bool:
        """Insert a single question into database"""
        try:
            self._ensure_connection()
            
            # Validate required fields
            required_fields = ['question', 'level']
            for field in required_fields:
                if field not in question:
                    raise ValueError(f"Missing required field: {field}")
            
            result = await self.questions_collection.insert_one(question)
            
            if result.inserted_id is not None:
                print(f"Successfully inserted question with ID: {result.inserted_id}")
                return True
            else:
                print("Failed to insert question")
                return False
                
        except Exception as e:
            print(f"Error inserting question: {str(e)}")
            return False
    
    async def insert_questions_bulk(self, questions: List[Dict[str, Any]]) -> int:
        """Insert multiple questions into database"""
        try:
            self._ensure_connection()
            
            if not questions:
                return 0
            
            # Validate all questions
            for i, question in enumerate(questions):
                required_fields = ['question', 'level']
                for field in required_fields:
                    if field not in question:
                        raise ValueError(f"Question {i+1} missing required field: {field}")
            
            result = await self.questions_collection.insert_many(questions)
            
            inserted_count = len(result.inserted_ids) if result.inserted_ids is not None else 0
            print(f"Successfully inserted {inserted_count} questions")
            return inserted_count
            
        except Exception as e:
            print(f"Error inserting questions in bulk: {str(e)}")
            return 0
    
    async def delete_all_questions(self) -> int:
        """Delete all questions from database"""
        try:
            self._ensure_connection()
            
            result = await self.questions_collection.delete_many({})
            deleted_count = result.deleted_count if result.deleted_count is not None else 0
            
            print(f"Deleted {deleted_count} questions")
            return deleted_count
            
        except Exception as e:
            print(f"Error deleting questions: {str(e)}")
            return 0
    
    async def delete_questions_by_level(self, level: str) -> int:
        """Delete questions by DMAIC-S level"""
        try:
            self._ensure_connection()
            
            result = await self.questions_collection.delete_many({"level": level})
            deleted_count = result.deleted_count if result.deleted_count is not None else 0
            
            print(f"Deleted {deleted_count} questions for level: {level}")
            return deleted_count
            
        except Exception as e:
            print(f"Error deleting questions for level {level}: {str(e)}")
            return 0
    
    async def get_levels_with_questions(self) -> List[str]:
        """Get all DMAIC-S levels that have questions"""
        try:
            self._ensure_connection()
            
            # Use aggregation to get distinct levels
            pipeline = [
                {"$group": {"_id": "$level"}},
                {"$sort": {"_id": 1}}
            ]
            
            levels = []
            async for doc in self.questions_collection.aggregate(pipeline):
                if doc['_id'] is not None:  # Check for None explicitly
                    levels.append(doc['_id'])
            
            print(f"Found levels with questions: {levels}")
            return levels
            
        except Exception as e:
            print(f"Error getting levels with questions: {str(e)}")
            return []
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform database health check"""
        try:
            if self.client is None:
                return {
                    "status": "disconnected",
                    "connected": False,
                    "error": "Database client not initialized"
                }
            
            # Test connection
            await self.client.admin.command('ping')
            
            # Get collection stats
            total_questions = await self.count_questions()
            levels_with_questions = await self.get_levels_with_questions()
            
            return {
                "status": "healthy",
                "connected": True,
                "database": self.database_name,
                "collection": self.collection_name,
                "total_questions": total_questions,
                "levels_with_questions": levels_with_questions,
                "connection_string": self.connection_string.replace(
                    self.connection_string.split('@')[-1], 
                    '@***'
                ) if '@' in self.connection_string else self.connection_string
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e)
            }

# Global database service instance
db_service = DatabaseService()

# Convenience functions for backward compatibility
async def connect_db():
    """Connect to database"""
    await db_service.connect()

async def disconnect_db():
    """Disconnect from database"""
    await db_service.disconnect()

async def get_questions_by_level(level: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Get questions by level"""
    return await db_service.get_questions_by_level(level, limit)

async def count_questions() -> int:
    """Count total questions"""
    return await db_service.count_questions()

async def count_questions_by_level(level: str) -> int:
    """Count questions by level"""
    return await db_service.count_questions_by_level(level)