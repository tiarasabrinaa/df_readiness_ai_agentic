from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from passlib.context import CryptContext
from sqlalchemy.dialects.postgresql import UUID
import uuid

# Global SQLAlchemy instance (will be initialized in main)
db = SQLAlchemy()
_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = db.Column(db.String(255), unique=True, nullable=True, index=True)
    email = db.Column(db.String(255), unique=True, nullable=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    refresh_token_jti = db.Column(db.String(36), nullable=True)  # last valid refresh token id

    def set_password(self, password: str):
        self.password_hash = _pwd_ctx.hash(password)

    def verify_password(self, password: str) -> bool:
        return _pwd_ctx.verify(password, self.password_hash)

    def to_dict(self):
        return {
            'id': str(self.id),
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }
