# services/database_service.py
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from typing import Dict, List, Optional
from bson import ObjectId
import logging
import asyncio
from config.settings import settings

logger = logging.getLogger(__name__)

class DataBaseServiceVersion1:
    """MongoDB Database Service with both async and sync methods"""
    
    def __init__(self):
        # Async client (Motor)
        self.async_client: Optional[AsyncIOMotorClient] = None
        self.async_db = None
        
        # Sync client (PyMongo)
        self.sync_client: Optional[MongoClient] = None
        self.sync_db = None
        
        self.questions_collection = None
        self.keterangan_collection = None
        self._async_connected = False
        self._sync_connected = False
        
    def _get_connection_string(self):
        """Build MongoDB connection string"""
        username = getattr(settings, 'MONGODB_USERNAME', 'admin')
        password = getattr(settings, 'MONGODB_PASSWORD', 'securepassword123')
        host = getattr(settings, 'MONGODB_HOST', 'mongodb')
        port = getattr(settings, 'MONGODB_PORT', 27017)
        database = getattr(settings, 'MONGODB_DATABASE', 'cybersecurity_assessment')
        
        return f"mongodb://{username}:{password}@{host}:{port}/{database}?authSource=admin", database
    
    def connect_sync(self):
        """Connect to MongoDB using sync client (PyMongo)"""
        if self._sync_connected:
            logger.info("Already connected to MongoDB (sync)")
            return
            
        try:
            connection_string, database = self._get_connection_string()
            
            # Create sync MongoDB client
            self.sync_client = MongoClient(connection_string)
            
            # Test connection
            self.sync_client.admin.command('ping')
            
            # Initialize database and collections
            self.sync_db = self.sync_client[database]
            self.questions_collection = self.sync_db.question_before_v1
            self.keterangan_collection = self.sync_db.keterangan
            
            self._sync_connected = True
            logger.info(f"MongoDB connected (sync) to database '{database}'")
            
        except Exception as e:
            logger.error(f"MongoDB sync connection failed: {e}")
            self._sync_connected = False
            raise
    
    def ensure_sync_connected(self):
        """Ensure sync database is connected before operations"""
        if not self._sync_connected:
            self.connect_sync()
    
    
    def get_questions_by_package_sync(self, package: str, limit: int = 15) -> List[Dict]:
        """Get questions filtered by package with limit (SYNC)"""
        try:
            self.ensure_sync_connected()
            
            query = {"id_package": package}
            cursor = self.questions_collection.find(query).limit(limit)
            questions = []
            
            for doc in cursor:
                question_dict = {
                    "id": str(doc["_id"]),
                    "question": doc.get("question", ""),
                    "package": doc.get("id_package", ""),
                    "level": doc.get("level", "basic"),
                    "category": doc.get("category", "general"),
                    "indicator": doc.get("indicator", ""),
                    "created_at": doc.get("created_at"),
                    "updated_at": doc.get("updated_at")
                }
                
                if question_dict["question"]:
                    questions.append(question_dict)
            
            logger.info(f"Retrieved {len(questions)} questions for package '{package}'")
            return questions
            
        except Exception as e:
            logger.error(f"Error getting questions by package '{package}': {e}")
            return []
    
    def count_questions_sync(self) -> int:
        """Count total questions in database (SYNC)"""
        try:
            self.ensure_sync_connected()
            count = self.questions_collection.count_documents({})
            return count
        except Exception as e:
            logger.error(f"Error counting questions: {e}")
            return 0
    
    def get_all_questions_sync(self) -> List[Dict]:
        """Get all questions from database (SYNC)"""
        try:
            self.ensure_sync_connected()
            
            cursor = self.questions_collection.find({})
            questions = []
            
            for doc in cursor:
                question_dict = {
                    "id": str(doc.get("_id", "")),
                    "question": doc.get("question", doc.get("pertanyaan", "")),
                    "package": doc.get("package", doc.get("paket", "basic")),
                    "level": doc.get("level", "basic"),
                    "category": doc.get("category", doc.get("kategori", "general")),
                    "indikator": doc.get("indikator", ""),
                    "created_at": doc.get("created_at"),
                    "updated_at": doc.get("updated_at")
                }
                
                if question_dict["question"]:
                    questions.append(question_dict)
            
            logger.info(f"Retrieved {len(questions)} questions from database")
            return questions
            
        except Exception as e:
            logger.error(f"Error getting all questions: {e}")
            return []
    
    def get_packages_list_sync(self) -> List[str]:
        """Get list of unique packages (SYNC)"""
        try:
            self.ensure_sync_connected()
            
            packages = set()
            
            # Get packages from questions collection
            questions_packages = self.questions_collection.distinct("id_package")
            packages.update(questions_packages)
            
            paket_packages = self.questions_collection.distinct("paket")
            packages.update(paket_packages)
            
            # Get packages from keterangan collection
            keterangan_packages = self.keterangan_collection.distinct("package")
            packages.update(keterangan_packages)
            
            keterangan_paket = self.keterangan_collection.distinct("paket")
            packages.update(keterangan_paket)
            
            # Filter out None and empty values
            packages = {pkg for pkg in packages if pkg}
            
            logger.info(f"Found {len(packages)} unique packages: {sorted(packages)}")
            return sorted(list(packages))
            
        except Exception as e:
            logger.error(f"Error getting packages list: {e}")
            return ["basic"]
    
    # === ASYNC METHODS (keep existing for compatibility) ===
    
    async def connect(self):
        """Connect to MongoDB (async)"""
        if self._async_connected:
            logger.info("Already connected to MongoDB (async)")
            return
            
        try:
            connection_string, database = self._get_connection_string()
            
            self.async_client = AsyncIOMotorClient(connection_string)
            await self.async_client.admin.command('ping')
            
            self.async_db = self.async_client[database]
            
            self._async_connected = True
            logger.info(f"MongoDB connected (async) to database '{database}'")
            
        except Exception as e:
            logger.error(f"MongoDB async connection failed: {e}")
            self._async_connected = False
            raise
    
    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.async_client and self._async_connected:
            self.async_client.close()
            self._async_connected = False
        if self.sync_client and self._sync_connected:
            self.sync_client.close()
            self._sync_connected = False
        logger.info("MongoDB disconnected")
    
    async def ensure_connected(self):
        """Ensure async database is connected"""
        if not self._async_connected:
            await self.connect()
    
    async def get_questions_by_package(self, package: str, limit: int = 15) -> List[Dict]:
        """Get questions filtered by package (ASYNC - keep for compatibility)"""
        try:
            await self.ensure_connected()
            
            questions_collection = self.async_db.question_before_v1
            query = {"id_package": package}
            cursor = questions_collection.find(query).limit(limit)
            questions = []
            
            async for doc in cursor:
                question_dict = {
                    "id": str(doc["_id"]),
                    "question": doc.get("question", ""),
                    "package": doc.get("id_package", ""),
                    "level": doc.get("level", "basic"),
                    "category": doc.get("category", "general"),
                    "indicator": doc.get("indicator", ""),
                    "created_at": doc.get("created_at"),
                    "updated_at": doc.get("updated_at")
                }
                
                if question_dict["question"]:
                    questions.append(question_dict)
            
            logger.info(f"Retrieved {len(questions)} questions for package '{package}'")
            return questions
            
        except Exception as e:
            logger.error(f"Error getting questions by package '{package}': {e}")
            return []
    
    async def count_questions(self) -> int:
        """Count total questions (async)"""
        try:
            await self.ensure_connected()
            count = await self.async_db.question_before_v1.count_documents({})
            return count
        except Exception as e:
            logger.error(f"Error counting questions: {e}")
            return 0

class DataBaseServiceVersion2:
    """MongoDB Database Service for question_before_v2 collection"""
    
    def __init__(self):
        # Async client (Motor)
        self.async_client: Optional[AsyncIOMotorClient] = None
        self.async_db = None
        
        # Sync client (PyMongo)
        self.sync_client: Optional[MongoClient] = None
        self.sync_db = None
        
        self.questions_collection = None
        self.keterangan_collection = None
        self._async_connected = False
        self._sync_connected = False
        
    def _get_connection_string(self):
        """Build MongoDB connection string"""
        username = getattr(settings, 'MONGODB_USERNAME', 'admin')
        password = getattr(settings, 'MONGODB_PASSWORD', 'securepassword123')
        host = getattr(settings, 'MONGODB_HOST', 'mongodb')
        port = getattr(settings, 'MONGODB_PORT', 27017)
        database = getattr(settings, 'MONGODB_DATABASE', 'cybersecurity_assessment')
        
        return f"mongodb://{username}:{password}@{host}:{port}/{database}?authSource=admin", database
    
    def connect_sync(self):
        """Connect to MongoDB using sync client (PyMongo)"""
        if self._sync_connected:
            logger.info("Already connected to MongoDB v2 (sync)")
            return
            
        try:
            connection_string, database = self._get_connection_string()
            
            self.sync_client = MongoClient(connection_string)
            self.sync_client.admin.command('ping')
            
            # Initialize database and collections - V2
            self.sync_db = self.sync_client[database]
            self.questions_collection = self.sync_db.question_before_v2  # ✅ v2
            self.keterangan_collection = self.sync_db.keterangan
            
            self._sync_connected = True
            logger.info(f"MongoDB v2 connected (sync) to database '{database}'")
            
        except Exception as e:
            logger.error(f"MongoDB v2 sync connection failed: {e}")
            self._sync_connected = False
            raise
    
    def ensure_sync_connected(self):
        """Ensure sync database is connected before operations"""
        if not self._sync_connected:
            self.connect_sync()
    
    def count_questions_sync(self) -> int:
        """Count total questions in database (SYNC) - V2"""
        try:
            self.ensure_sync_connected()
            count = self.questions_collection.count_documents({})
            return count
        except Exception as e:
            logger.error(f"Error counting v2 questions: {e}")
            return 0
        
    def get_questions_by_package_sync(self, package: str, limit: int = 15) -> List[Dict]:
        """Get questions filtered by package with limit (SYNC) - V2"""
        try:
            self.ensure_sync_connected()
            
            query = {"id_package": package}
            cursor = self.questions_collection.find(query).limit(limit)
            questions = []
            
            for doc in cursor:
                question_dict = {
                    "id": str(doc["_id"]),
                    "question": doc.get("question", ""),
                    "package": doc.get("id_package", ""),
                    "enabler": doc.get("enabler", ""),
                    "indicator": doc.get("indicator", ""),
                    "contribution_max": doc.get("contribution_max", 0),
                    "sum_contribution_max": doc.get("sum_contribution_max", 0),
                    "generated_at": doc.get("generated_at", ""),
                    "created_at": doc.get("created_at"),
                    "updated_at": doc.get("updated_at")
                }
                
                if question_dict["question"]:
                    questions.append(question_dict)
            
            logger.info(f"Retrieved {len(questions)} v2 questions for package '{package}'")
            return questions
            
        except Exception as e:
            logger.error(f"Error getting v2 questions by package '{package}': {e}")
            return []
    
    def get_all_questions_sync(self) -> List[Dict]:
        """Get all questions from database (SYNC) - V2"""
        try:
            self.ensure_sync_connected()
            
            cursor = self.questions_collection.find({})
            questions = []
            
            for doc in cursor:
                question_dict = {
                    "id": str(doc.get("_id", "")),
                    "question": doc.get("question", ""),
                    "package": doc.get("id_package", ""),
                    "enabler": doc.get("enabler", ""),
                    "indicator": doc.get("indicator", ""),
                    "generated_at": doc.get("generated_at", ""),
                    "created_at": doc.get("created_at"),
                    "updated_at": doc.get("updated_at")
                }
                
                if question_dict["question"]:
                    questions.append(question_dict)
            
            logger.info(f"Retrieved {len(questions)} v2 questions from database")
            return questions
            
        except Exception as e:
            logger.error(f"Error getting all v2 questions: {e}")
            return []
    
    def get_packages_list_sync(self) -> List[str]:
        """Get list of unique packages (SYNC) - V2"""
        try:
            self.ensure_sync_connected()
            
            packages = set()
            
            # Get packages from v2 questions collection
            questions_packages = self.questions_collection.distinct("id_package")
            packages.update(questions_packages)
            
            # Filter out None and empty values
            packages = {pkg for pkg in packages if pkg}
            
            logger.info(f"Found {len(packages)} unique v2 packages: {sorted(packages)}")
            return sorted(list(packages))
            
        except Exception as e:
            logger.error(f"Error getting v2 packages list: {e}")
            return []
    
    def get_questions_by_enabler_sync(self, enabler: str, limit: int = 20) -> List[Dict]:
        """Get questions filtered by enabler (SYNC) - V2 specific"""
        try:
            self.ensure_sync_connected()
            
            query = {"enabler": enabler}
            cursor = self.questions_collection.find(query).limit(limit)
            questions = []
            
            for doc in cursor:
                question_dict = {
                    "id": str(doc["_id"]),
                    "question": doc.get("question", ""),
                    "package": doc.get("id_package", ""),
                    "enabler": doc.get("enabler", ""),
                    "indicator": doc.get("indicator", ""),
                    "generated_at": doc.get("generated_at", ""),
                    "created_at": doc.get("created_at"),
                    "updated_at": doc.get("updated_at")
                }
                
                if question_dict["question"]:
                    questions.append(question_dict)
            
            logger.info(f"Retrieved {len(questions)} v2 questions for enabler '{enabler}'")
            return questions
            
        except Exception as e:
            logger.error(f"Error getting v2 questions by enabler '{enabler}': {e}")
            return []
    
    def get_enablers_list_sync(self) -> List[str]:
        """Get list of unique enablers (SYNC) - V2 specific"""
        try:
            self.ensure_sync_connected()
            
            enablers = self.questions_collection.distinct("enabler")
            enablers = [e for e in enablers if e]  # Filter None/empty
            
            logger.info(f"Found {len(enablers)} unique enablers")
            return sorted(enablers)
            
        except Exception as e:
            logger.error(f"Error getting enablers list: {e}")
            return []
    
    # === ASYNC METHODS ===
    
    async def connect(self):
        """Connect to MongoDB (async) - V2"""
        if self._async_connected:
            logger.info("Already connected to MongoDB v2 (async)")
            return
            
        try:
            connection_string, database = self._get_connection_string()
            
            self.async_client = AsyncIOMotorClient(connection_string)
            await self.async_client.admin.command('ping')
            
            self.async_db = self.async_client[database]
            
            self._async_connected = True
            logger.info(f"MongoDB v2 connected (async) to database '{database}'")
            
        except Exception as e:
            logger.error(f"MongoDB v2 async connection failed: {e}")
            self._async_connected = False
            raise
    
    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.async_client and self._async_connected:
            self.async_client.close()
            self._async_connected = False
        if self.sync_client and self._sync_connected:
            self.sync_client.close()
            self._sync_connected = False
        logger.info("MongoDB v2 disconnected")
    
    async def ensure_connected(self):
        """Ensure async database is connected"""
        if not self._async_connected:
            await self.connect()
    
    async def get_questions_by_package(self, package: str, limit: int = 15) -> List[Dict]:
        """Get questions filtered by package (ASYNC) - V2"""
        try:
            await self.ensure_connected()
            
            questions_collection = self.async_db.question_before_v2
            query = {"id_package": package}
            cursor = questions_collection.find(query).limit(limit)
            questions = []
            
            async for doc in cursor:
                question_dict = {
                    "id": str(doc["_id"]),
                    "question": doc.get("question", ""),
                    "package": doc.get("id_package", ""),
                    "enabler": doc.get("enabler", ""),
                    "indicator": doc.get("indicator", ""),
                    "generated_at": doc.get("generated_at", ""),
                    "created_at": doc.get("created_at"),
                    "updated_at": doc.get("updated_at")
                }
                
                if question_dict["question"]:
                    questions.append(question_dict)
            
            logger.info(f"Retrieved {len(questions)} v2 questions for package '{package}'")
            return questions
            
        except Exception as e:
            logger.error(f"Error getting v2 questions by package '{package}': {e}")
            return []
    
    async def count_questions(self) -> int:
        """Count total questions (async) - V2"""
        try:
            await self.ensure_connected()
            count = await self.async_db.question_before_v2.count_documents({})
            return count
        except Exception as e:
            logger.error(f"Error counting v2 questions: {e}")
            return 0


# Global singleton instances
db_service_v1 = DataBaseServiceVersion1()
db_service_v2 = DataBaseServiceVersion2()

# Default to v1 for backward compatibility
db_service = db_service_v1