# api/base/base_schemas.py
from typing import Generic, Optional, TypeVar
from pydantic import BaseModel, Field, ConfigDict

T = TypeVar("T")

class BaseResponse(BaseModel, Generic[T]):
    model_config = ConfigDict(exclude_none=True)
    
    status: str = Field(..., description="'success' or 'error'")
    message: Optional[str] = Field(None, description="Human-friendly message")
    errors: Optional[T] = Field(None, description="Error details")
    data: Optional[T] = Field(None, description="Payload data")

    @classmethod
    def success(cls, data: Optional[T] = None, message: Optional[str] = None):
        return cls(status="success", message=message, data=data)

    @classmethod
    def error(cls, message: str, errors: Optional[T] = None):
        return cls(status="error", message=message, errors=errors)