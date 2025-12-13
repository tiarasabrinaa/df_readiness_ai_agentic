import csv
import json
import time
import os
import logging
from pymongo import MongoClient
from typing import List, Dict, Any
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MongoDBConfig:
    """MongoDB configuration from environment variables"""
    
    @staticmethod
    def get_connection_string() -> str:
        host = os.getenv('MONGO_HOST', 'mongodb')
        port = os.getenv('MONGO_PORT', '27017')
        username = os.getenv('MONGO_USERNAME', 'admin')
        password = os.getenv('MONGO_PASSWORD', 'securepassword123')
        auth_db = os.getenv('MONGO_AUTH_DB', 'admin')
        
        return f'mongodb://{username}:{password}@{host}:{port}/?authSource={auth_db}'
    
    @staticmethod
    def get_database_name() -> str:
        return os.getenv('MONGO_DATABASE', 'cybersecurity_assessment')

def get_questions_all_v2() -> List[Dict[str, Any]]:
    """Fetch all questions from the MongoDB collection 'question_before_v2'"""
    try:
        connection_string = MongoDBConfig.get_connection_string()
        database_name = MongoDBConfig.get_database_name()
        
        client = MongoClient(connection_string)
        db = client[database_name]
        questions_collection = db['question_before_v2']
        
        questions_cursor = questions_collection.find({})
        questions = list(questions_cursor)
        
        logger.info(f"Fetched {len(questions)} questions from the database.")
        return questions
    except Exception as e:
        logger.error(f"Error fetching questions: {str(e)}")
        return []