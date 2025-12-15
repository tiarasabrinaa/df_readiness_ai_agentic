"""
Questions V1 Service - question_before_v1 collection
"""
from typing import List, Dict
from ..base import BaseMongoService, logger


class QuestionsV1Service(BaseMongoService):
    """Service for question_before_v1 collection"""
    
    def __init__(self):
        super().__init__("question_before_v1")
    
    def get_by_package(self, package: str, limit: int = 15) -> List[Dict]:
        """
        Get questions filtered by package
        
        Args:
            package: Package ID (e.g., "qb_v1_000")
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
                    "level": doc.get("level", "basic"),
                    "category": doc.get("category", "general"),
                    "indicator": doc.get("indicator", ""),
                    "created_at": doc.get("created_at"),
                    "updated_at": doc.get("updated_at")
                })
            
            logger.info(f"Retrieved {len(questions)} v1 questions for package '{package}'")
            return questions
            
        except Exception as e:
            logger.error(f"Error getting v1 questions: {e}")
            return []
    
    def count(self) -> int:
        """Count total questions in collection"""
        try:
            self.ensure_connected()
            return self.collection.count_documents({})
        except Exception as e:
            logger.error(f"Error counting v1 questions: {e}")
            return 0
    
    def get_all(self) -> List[Dict]:
        """Get all questions from collection"""
        try:
            self.ensure_connected()
            
            cursor = self.collection.find({})
            questions = []
            
            for doc in cursor:
                questions.append({
                    "id": str(doc.get("_id", "")),
                    "question": doc.get("question", ""),
                    "package": doc.get("id_package", ""),
                    "level": doc.get("level", "basic"),
                    "category": doc.get("category", "general"),
                    "indicator": doc.get("indicator", ""),
                })
            
            return questions
            
        except Exception as e:
            logger.error(f"Error getting all v1 questions: {e}")
            return []
    
    def get_packages(self) -> List[str]:
        """Get list of unique packages"""
        try:
            self.ensure_connected()
            packages = self.collection.distinct("id_package")
            return sorted([p for p in packages if p])
        except Exception as e:
            logger.error(f"Error getting v1 packages: {e}")
            return []
