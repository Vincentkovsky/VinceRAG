"""
User model for authentication
"""

from sqlalchemy import Column, String, Boolean, DateTime, BigInteger
from sqlalchemy.sql import func
from datetime import datetime

from ..core.database import Base
from ..core.snowflake import generate_id


class User(Base):
    """User model for authentication"""
    
    __tablename__ = "users"
    
    id = Column(BigInteger, primary_key=True, default=generate_id)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', is_active={self.is_active})>"