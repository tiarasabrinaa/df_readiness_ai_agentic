# features/assessment_before/schemas.py
from typing import List, Dict, Optional
from pydantic import BaseModel, Field

# REQUEST SCHEMAS
class EmailRequest(BaseModel):
    """Request body for POST /submit_test_answers"""
    email: str

# RESPONSE SCHEMAS
class EmailResponse(BaseModel):
    """Response data for email submission"""
    session_id: str
    email: str
    message: str