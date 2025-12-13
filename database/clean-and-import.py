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


class CSVImporter:
    """Handle CSV/JSON import to MongoDB collections"""
    
    def __init__(self, db_name: str = None):
        self.connection_string = MongoDBConfig.get_connection_string()
        self.db_name = db_name or MongoDBConfig.get_database_name()
        self.client = None
        self.db = None
        
    def connect(self) -> bool:
        """Establish MongoDB connection"""
        try:
            self.client = MongoClient(self.connection_string)
            self.client.admin.command('ping')
            self.db = self.client[self.db_name]
            logger.info(f"Connected to MongoDB database: {self.db_name}")
            return True
        except Exception as e:
            logger.error(f"MongoDB connection failed: {e}")
            return False
    
    def disconnect(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")
    
    def drop_collection(self, collection_name: str) -> bool:
        """Drop existing collection"""
        try:
            self.db[collection_name].drop()
            logger.info(f"Collection '{collection_name}' dropped")
            return True
        except Exception as e:
            logger.warning(f"Could not drop collection '{collection_name}': {e}")
            return False
    
    def import_keterangan(self, csv_path: str) -> int:
        """Import keterangan CSV to MongoDB"""
        collection = self.db.keterangan
        documents = []
        
        if not os.path.exists(csv_path):
            logger.error(f"File not found: {csv_path}")
            return 0
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as csvfile:
                sample = csvfile.read(1024)
                csvfile.seek(0)
                delimiter = ',' if ',' in sample else ';'
                
                reader = csv.DictReader(csvfile, delimiter=delimiter)
                logger.info(f"Reading keterangan CSV with delimiter: '{delimiter}'")
                
                for row in reader:
                    if not any(row.values()):
                        continue
                    
                    doc = {
                        'package': row.get('Package', '').strip(),
                        'keterangan': row.get('Keterangan', '').strip(),
                        'created_at': datetime.now().isoformat(),
                        'updated_at': datetime.now().isoformat()
                    }
                    
                    embedded_value = row.get('embedded', '').strip()
                    if embedded_value:
                        try:
                            doc['embedded'] = json.loads(embedded_value)
                        except json.JSONDecodeError:
                            doc['embedded'] = []
                    
                    if doc['package'] and doc['keterangan']:
                        documents.append(doc)
            
            if documents:
                result = collection.insert_many(documents)
                logger.info(f"Imported {len(result.inserted_ids)} documents to 'keterangan'")
                return len(result.inserted_ids)
            else:
                logger.warning("No valid documents found in keterangan CSV")
                return 0
                
        except Exception as e:
            logger.error(f"Error importing keterangan: {e}")
            return 0
    
    def import_questions_v1(self, csv_path: str, package_id: str = "qb_v1_000") -> int:
        """Import questions CSV to question_before_v1 collection"""
        collection = self.db.question_before_v1
        documents = []
        
        if not os.path.exists(csv_path):
            logger.error(f"File not found: {csv_path}")
            return 0
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile, delimiter=';')
                logger.info("Reading questions CSV for v1")
                
                for row in reader:
                    if not any(row.values()):
                        continue
                    
                    doc = {
                        'id_package': package_id,
                        'level': row.get('Level', row.get('level', '')).strip(),
                        'indicator': row.get('Indikator', row.get('indikator', '')).strip(),
                        'question': row.get('Pertanyaan', row.get('pertanyaan', '')).strip(),
                        'created_at': datetime.now().isoformat(),
                        'updated_at': datetime.now().isoformat()
                    }
                    
                    if doc['question']:
                        documents.append(doc)
            
            if documents:
                result = collection.insert_many(documents)
                logger.info(f"Imported {len(result.inserted_ids)} documents to 'question_before_v1'")
                return len(result.inserted_ids)
            else:
                logger.warning("No valid documents found in questions CSV")
                return 0
                
        except Exception as e:
            logger.error(f"Error importing questions v1: {e}")
            return 0
    
    def import_questions_v2(self, json_path: str, package_id: str = "qb_v2_000") -> int:
        """Import generated questions JSON to question_before_v2 collection"""
        collection = self.db.question_before_v2
        documents = []
        
        if not os.path.exists(json_path):
            logger.error(f"File not found: {json_path}")
            return 0
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            metadata = data.get('metadata', {})
            enablers = data.get('enablers', [])
            
            logger.info(f"Processing JSON v2 - Model: {metadata.get('model')}, Version: {metadata.get('version')}")
            
            for enabler in enablers:
                enabler_id = enabler.get('enabler_id')
                enabler_name = enabler.get('enabler_name')
                questions = enabler.get('questions', [])
                contribution_max = enabler.get('contribution_max', 4)
                sum_contribution_max = enabler.get('sum_contribution_max', 0)
                
                for q in questions:
                    doc = {
                        'id_package': package_id,
                        'enabler': f"{enabler_id}. {enabler_name}",
                        'indicator': q.get('indicator', ''),
                        'question': q.get('question', ''),
                        'contribution_max': q.get('contribution_max', contribution_max),
                        'sum_contribution_max': sum_contribution_max,
                        'generated_at': metadata.get('generated_at'),
                        'created_at': datetime.now().isoformat(),
                        'updated_at': datetime.now().isoformat()
                    }
                    
                    if doc['question']:
                        documents.append(doc)
            
            if documents:
                result = collection.insert_many(documents)
                logger.info(f"Imported {len(result.inserted_ids)} documents to 'question_before_v2'")
                return len(result.inserted_ids)
            else:
                logger.warning("No valid documents found in JSON v2")
                return 0
                
        except Exception as e:
            logger.error(f"Error importing questions v2: {e}")
            import traceback
            traceback.print_exc()
            return 0
    
    def verify_import(self):
        """Verify imported data"""
        collections_info = {
            'keterangan': self.db.keterangan.count_documents({}),
            'question_before_v1': self.db.question_before_v1.count_documents({}),
            'question_before_v2': self.db.question_before_v2.count_documents({})
        }
        
        logger.info("Import verification:")
        for collection_name, count in collections_info.items():
            logger.info(f"  {collection_name}: {count} documents")
        
        for collection_name in collections_info.keys():
            sample = self.db[collection_name].find_one()
            if sample:
                logger.info(f"Sample from {collection_name}:")
                logger.info(json.dumps(sample, default=str, indent=2))


def main():
    """Main import process"""
    time.sleep(5)
    
    keterangan_csv = '/database/keterangan.csv'
    questions_v1_csv = '/database/data_wisang.csv'
    questions_v2_json = '/database/generated_questions_08122025_0138.json'
    
    importer = CSVImporter()
    
    if not importer.connect():
        logger.error("Failed to connect to MongoDB")
        return
    
    try:
        importer.drop_collection('keterangan')
        importer.drop_collection('question_before_v1')
        importer.drop_collection('question_before_v2')
        
        keterangan_count = importer.import_keterangan(keterangan_csv)
        v1_count = importer.import_questions_v1(questions_v1_csv, package_id="qb_v1_000")
        v2_count = importer.import_questions_v2(questions_v2_json, package_id="qb_v2_000")
        
        importer.verify_import()
        
        logger.info("Import completed successfully")
        logger.info(f"Summary - Keterangan: {keterangan_count}, V1: {v1_count}, V2: {v2_count}")
        
    except Exception as e:
        logger.error(f"Import failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        importer.disconnect()


if __name__ == "__main__":
    main()