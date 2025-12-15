"""
Questions V2 Service - question_before_v2 collection
"""
from typing import List, Dict
import json
import logging
from ..base import BaseMongoService, logger


logger = logging.getLogger("debug_logger")

class QuestionsV2Service(BaseMongoService):
    """Service for question_before_v2 collection"""
    
    def __init__(self):
        super().__init__("question_before_v2")
    
    def get_by_package(self, package: str, limit: int = 15) -> List[Dict]:
        """
        Get questions filtered by package
        
        Args:
            package: Package ID
            limit: Maximum number of questions
            
        Returns:
            List of question dictionaries
        """
        try:
            self.ensure_connected()
            
            query = {"id_package": package}
            cursor = self.collection.find(query).limit(limit)
            
            questions = []
            for doc in cursor:
                questions.append({
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
                })
            
            logger.info(f"Retrieved {len(questions)} v2 questions for package '{package}'")
            return questions
            
        except Exception as e:
            logger.error(f"Error getting v2 questions: {e}")
            return []
    
    def get_by_enabler(self, enabler: str, limit: int = 20) -> List[Dict]:
        """
        Get questions filtered by enabler (V2 specific feature)
        
        Args:
            enabler: Enabler code (e.g., "APO01")
            limit: Maximum number of questions
            
        Returns:
            List of question dictionaries
        """
        try:
            self.ensure_connected()
            
            query = {"enabler": enabler}
            cursor = self.collection.find(query).limit(limit)
            
            questions = []
            for doc in cursor:
                questions.append({
                    "id": str(doc["_id"]),
                    "question": doc.get("question", ""),
                    "enabler": doc.get("enabler", ""),
                    "indicator": doc.get("indicator", ""),
                    "package": doc.get("id_package", "")
                })
            
            logger.info(f"Retrieved {len(questions)} v2 questions for enabler '{enabler}'")
            return questions
            
        except Exception as e:
            logger.error(f"Error getting v2 questions by enabler: {e}")
            return []
    
    def count(self) -> int:
        """Count total questions in collection"""
        try:
            self.ensure_connected()
            return self.collection.count_documents({})
        except Exception as e:
            logger.error(f"Error counting v2 questions: {e}")
            return 0
    
    def get_all(self) -> List[Dict]:
        """Get all questions from collection"""
        try:
            self.ensure_connected()
            
            cursor = self.collection.find({})
            questions = []
            
            for doc in cursor:
                logger.debug(f"Question Document: {json.dumps(doc, default=str)}")

                questions.append({
                    "id": str(doc.get("_id", "")),
                    "question": doc.get("question", ""),
                    "package": doc.get("id_package", ""),
                    "enabler": doc.get("enabler", ""),
                    "indicator": doc.get("indicator", ""),
                    "contribution_max": doc.get("contribution_max", 0)
                })
            
            return questions
            
        except Exception as e:
            logger.error(f"Error getting all v2 questions: {e}")
            return []
    
    def get_enablers(self) -> List[str]:
        """Get list of unique enablers (V2 specific)"""
        try:
            self.ensure_connected()
            enablers = self.collection.distinct("enabler")
            return sorted([e for e in enablers if e])
        except Exception as e:
            logger.error(f"Error getting enablers: {e}")
            return []
    
    def get_packages(self) -> List[str]:
        """Get list of unique packages"""
        try:
            self.ensure_connected()
            packages = self.collection.distinct("id_package")
            return sorted([p for p in packages if p])
        except Exception as e:
            logger.error(f"Error getting v2 packages: {e}")
            return []
    
    def get_questions_per_enabler(self) -> List[Dict]:
        """
        Get 3 questions per enabler for quick test (V2 specific)
        
        Returns:
            List of question dictionaries
        """
        try:
            self.ensure_connected()
            enablers = self.get_enablers()
            selected_questions = []
            
            for enabler in enablers:
                query = {"enabler": enabler}
                cursor = self.collection.find(query).limit(3)
                
                for doc in cursor:
                    selected_questions.append({
                        "id": str(doc["_id"]),
                        "question": doc.get("question", ""),
                        "enabler": doc.get("enabler", ""),
                        "indicator": doc.get("indicator", ""),
                        "package": doc.get("id_package", "")
                    })
            
            logger.info(f"Retrieved {len(selected_questions)} questions for quick test")
            return selected_questions
            
        except Exception as e:
            logger.error(f"Error getting questions per enabler: {e}")
            return []
