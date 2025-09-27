# services/database_service.py
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Dict, List, Optional, Any
import logging
from config.settings import settings

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self):
        self.client = None
        self.db = None
        self.questions_collection = None
        self.keterangan_collection = None
        
    async def connect(self):
        """Connect to MongoDB"""
        try:
            # Create connection string
            if hasattr(settings, 'MONGODB_URL'):
                connection_string = settings.MONGODB_URL
            else:
                # Fallback to individual settings
                username = getattr(settings, 'MONGODB_USERNAME', 'admin')
                password = getattr(settings, 'MONGODB_PASSWORD', 'securepassword123')
                host = getattr(settings, 'MONGODB_HOST', 'mongodb')
                port = getattr(settings, 'MONGODB_PORT', 27017)
                database = getattr(settings, 'MONGODB_DATABASE', 'cybersecurity_assessment')
                
                connection_string = f"mongodb://{username}:{password}@{host}:{port}/{database}?authSource=admin"
            
            self.client = AsyncIOMotorClient(connection_string)
            
            # Test connection
            await self.client.admin.command('ping')
            logger.info("MongoDB connection successful")
            
            # Get database and collections
            self.db = self.client[getattr(settings, 'MONGODB_DATABASE', 'cybersecurity_assessment')]
            self.questions_collection = self.db.questions
            self.keterangan_collection = self.db.keterangan
            
            logger.info("Database and collections initialized")
            
        except Exception as e:
            logger.error(f"MongoDB connection failed: {e}")
            raise e
    
    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            logger.info("MongoDB disconnected")
    
    async def count_questions(self) -> int:
        """Count total questions in database"""
        try:
            if not self.questions_collection:
                await self.connect()
            
            count = await self.questions_collection.count_documents({})
            return count
        except Exception as e:
            logger.error(f"Error counting questions: {e}")
            return 0
    
    async def count_keterangan(self) -> int:
        """Count total keterangan documents in database"""
        try:
            if not self.keterangan_collection:
                await self.connect()
            
            count = await self.keterangan_collection.count_documents({})
            return count
        except Exception as e:
            logger.error(f"Error counting keterangan: {e}")
            return 0
    
    async def get_all_questions_from_database(self) -> List[Dict]:
        """Get all questions from database"""
        try:
            if not self.questions_collection:
                await self.connect()
            
            cursor = self.questions_collection.find({})
            questions = []
            
            async for doc in cursor:
                # Convert MongoDB document to dict and clean up
                question_dict = {
                    "id": str(doc.get("_id", "")),
                    "question": doc.get("question", doc.get("pertanyaan", "")),
                    "package": doc.get("package", doc.get("paket", "basic")),
                    "level": doc.get("level", "basic"),
                    "category": doc.get("category", doc.get("kategori", "general")),
                    "created_at": doc.get("created_at"),
                    "updated_at": doc.get("updated_at")
                }
                
                # Only add if question text exists
                if question_dict["question"]:
                    questions.append(question_dict)
            
            logger.info(f"Retrieved {len(questions)} questions from database")
            return questions
            
        except Exception as e:
            logger.error(f"Error getting all questions: {e}")
            return []
    
    async def get_all_keterangan(self) -> List[Dict]:
        """Get all keterangan documents from database"""
        try:
            if not self.keterangan_collection:
                await self.connect()
            
            cursor = self.keterangan_collection.find({})
            keterangan_docs = []
            
            async for doc in cursor:
                # Convert MongoDB document to dict and clean up
                keterangan_dict = {
                    "id": str(doc.get("_id", "")),
                    # Handle different field names from CSV
                    "package": doc.get("package", doc.get("Package", "0")),  
                    "description": doc.get("keterangan", doc.get("Keterangan", doc.get("description", ""))),
                    "embedded": doc.get("embedded", doc.get("embedding", "")),
                    "created_at": doc.get("created_at"),
                    "updated_at": doc.get("updated_at")
                }
                
                # Only add if description and embedding exist
                if keterangan_dict["description"] and keterangan_dict["embedded"]:
                    keterangan_docs.append(keterangan_dict)
            
            logger.info(f"Retrieved {len(keterangan_docs)} keterangan documents from database")
            return keterangan_docs
            
        except Exception as e:
            logger.error(f"Error getting all keterangan: {e}")
            return []
    
    async def get_questions_by_package(self, package: str, limit: int = 15) -> List[Dict]:
        """Get questions filtered by package with limit"""
        try:
            if not self.questions_collection:
                await self.connect()
            
            # Create query for package (check both 'package' and 'paket' fields)
            query = {
                "$or": [
                    {"package": package},
                    {"paket": package}
                ]
            }
            
            cursor = self.questions_collection.find(query).limit(limit)
            questions = []
            
            async for doc in cursor:
                # Convert MongoDB document to dict and clean up
                question_dict = {
                    "id": str(doc.get("_id", "")),
                    "question": doc.get("question", doc.get("pertanyaan", "")),
                    "package": doc.get("package", doc.get("paket", package)),
                    "level": doc.get("level", "basic"),
                    "category": doc.get("category", doc.get("kategori", "general")),
                    "created_at": doc.get("created_at"),
                    "updated_at": doc.get("updated_at")
                }
                
                # Only add if question text exists
                if question_dict["question"]:
                    questions.append(question_dict)
            
            logger.info(f"Retrieved {len(questions)} questions for package '{package}'")
            return questions
            
        except Exception as e:
            logger.error(f"Error getting questions by package '{package}': {e}")
            return []
    
    async def get_questions_by_level(self, level: str, limit: int = 10) -> List[Dict]:
        """Get questions filtered by level (keeping for backward compatibility)"""
        try:
            if not self.questions_collection:
                await self.connect()
            
            query = {"level": level}
            cursor = self.questions_collection.find(query).limit(limit)
            questions = []
            
            async for doc in cursor:
                question_dict = {
                    "id": str(doc.get("_id", "")),
                    "question": doc.get("question", doc.get("pertanyaan", "")),
                    "level": doc.get("level", level),
                    "package": doc.get("package", doc.get("paket", "basic")),
                    "category": doc.get("category", doc.get("kategori", "general")),
                    "created_at": doc.get("created_at"),
                    "updated_at": doc.get("updated_at")
                }
                
                if question_dict["question"]:
                    questions.append(question_dict)
            
            logger.info(f"Retrieved {len(questions)} questions for level '{level}'")
            return questions
            
        except Exception as e:
            logger.error(f"Error getting questions by level '{level}': {e}")
            return []
    
    async def get_keterangan_by_package(self, package: str) -> Optional[Dict]:
        """Get keterangan document by package"""
        try:
            if not self.keterangan_collection:
                await self.connect()
            
            # Create query for package (check both 'package' and 'paket' fields)
            query = {
                "$or": [
                    {"package": package},
                    {"paket": package}
                ]
            }
            
            doc = await self.keterangan_collection.find_one(query)
            
            if doc:
                keterangan_dict = {
                    "id": str(doc.get("_id", "")),
                    "description": doc.get("description", doc.get("deskripsi", "")),
                    "package": doc.get("package", doc.get("paket", package)),
                    "level": doc.get("level", "basic"),
                    "created_at": doc.get("created_at"),
                    "updated_at": doc.get("updated_at")
                }
                
                logger.info(f"Retrieved keterangan for package '{package}'")
                return keterangan_dict
            else:
                logger.warning(f"No keterangan found for package '{package}'")
                return None
                
        except Exception as e:
            logger.error(f"Error getting keterangan by package '{package}': {e}")
            return None
    
    async def insert_question(self, question_data: Dict) -> str:
        """Insert new question into database"""
        try:
            if not self.questions_collection:
                await self.connect()
            
            result = await self.questions_collection.insert_one(question_data)
            logger.info(f"Inserted question with ID: {result.inserted_id}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Error inserting question: {e}")
            raise e
    
    async def insert_keterangan(self, keterangan_data: Dict) -> str:
        """Insert new keterangan into database"""
        try:
            if not self.keterangan_collection:
                await self.connect()
            
            result = await self.keterangan_collection.insert_one(keterangan_data)
            logger.info(f"Inserted keterangan with ID: {result.inserted_id}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Error inserting keterangan: {e}")
            raise e
    
    async def update_question(self, question_id: str, update_data: Dict) -> bool:
        """Update existing question"""
        try:
            if not self.questions_collection:
                await self.connect()
            
            from bson import ObjectId
            result = await self.questions_collection.update_one(
                {"_id": ObjectId(question_id)}, 
                {"$set": update_data}
            )
            
            logger.info(f"Updated question {question_id}: {result.modified_count} document(s) modified")
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error updating question {question_id}: {e}")
            return False
    
    async def delete_question(self, question_id: str) -> bool:
        """Delete question from database"""
        try:
            if not self.questions_collection:
                await self.connect()
            
            from bson import ObjectId
            result = await self.questions_collection.delete_one({"_id": ObjectId(question_id)})
            
            logger.info(f"Deleted question {question_id}: {result.deleted_count} document(s) deleted")
            return result.deleted_count > 0
            
        except Exception as e:
            logger.error(f"Error deleting question {question_id}: {e}")
            return False
    
    async def get_packages_list(self) -> List[str]:
        """Get list of unique packages from both collections"""
        try:
            packages = set()
            
            # Get packages from questions collection
            if self.questions_collection:
                questions_packages = await self.questions_collection.distinct("package")
                packages.update(questions_packages)
                
                # Also check 'paket' field for Indonesian naming
                paket_packages = await self.questions_collection.distinct("paket")
                packages.update(paket_packages)
            
            # Get packages from keterangan collection
            if self.keterangan_collection:
                keterangan_packages = await self.keterangan_collection.distinct("package")
                packages.update(keterangan_packages)
                
                # Also check 'paket' field
                keterangan_paket = await self.keterangan_collection.distinct("paket")
                packages.update(keterangan_paket)
            
            # Filter out None and empty values
            packages = {pkg for pkg in packages if pkg}
            
            logger.info(f"Found {len(packages)} unique packages: {list(packages)}")
            return list(packages)
            
        except Exception as e:
            logger.error(f"Error getting packages list: {e}")
            return ["basic"]  # Return default package as fallback

# Create global instance
db_service = DatabaseService()