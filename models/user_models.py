# models/user_models.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId

class PersonalizationData(BaseModel):
    industry: Optional[str] = None
    company_size: Optional[str] = None
    role: Optional[str] = None
    experience_level: Optional[str] = None
    current_security_awareness: Optional[str] = None
    main_concerns: Optional[List[str]] = None
    preferred_learning_style: Optional[str] = None

class UserProfile(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={ObjectId: str}
    )
    
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    personalization: PersonalizationData
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)