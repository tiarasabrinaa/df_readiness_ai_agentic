from pymongo import MongoClient
from typing import Optional
from config.settings import settings
import logging

logger = logging.getLogger(__name__)


class BaseMongoService:
    """Base class for MongoDB collections"""
    
    def __init__(self, collection_name: str):
        self.collection_name = collection_name
        self.sync_client: Optional[MongoClient] = None
        self.sync_db = None
        self.collection = None
        self._connected = False
    
    def _get_connection_string(self):
        """Build MongoDB connection string"""
        username = getattr(settings, 'MONGODB_USERNAME', 'admin')
        password = getattr(settings, 'MONGODB_PASSWORD', 'securepassword123')
        host = getattr(settings, 'MONGODB_HOST', 'mongodb')
        port = getattr(settings, 'MONGODB_PORT', 27017)
        database = getattr(settings, 'MONGODB_DATABASE', 'cybersecurity_assessment')
        
        return f"mongodb://{username}:{password}@{host}:{port}/{database}?authSource=admin", database
    
    def connect(self):
        """Connect to MongoDB"""
        if self._connected:
            return
        
        try:
            connection_string, database = self._get_connection_string()
            
            self.sync_client = MongoClient(connection_string)
            self.sync_client.admin.command('ping')
            
            self.sync_db = self.sync_client[database]
            self.collection = self.sync_db[self.collection_name]
            
            self._connected = True
            logger.info(f"✓ Connected to '{self.collection_name}'")
            
        except Exception as e:
            logger.error(f"✗ Connection failed for '{self.collection_name}': {e}")
            self._connected = False
            raise
    
    def ensure_connected(self):
        """Ensure database is connected before operations"""
        if not self._connected:
            self.connect()
    
    def disconnect(self):
        """Disconnect from MongoDB"""
        if self.sync_client and self._connected:
            self.sync_client.close()
            self._connected = False