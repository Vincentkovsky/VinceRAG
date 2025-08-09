"""
Chat session and message models
"""

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, BigInteger, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

from ..core.database import Base
from ..core.snowflake import generate_id


class ChatSession(Base):
    """Chat session model for storing conversation sessions"""
    
    __tablename__ = "chat_sessions"
    
    id = Column(BigInteger, primary_key=True, default=generate_id)
    title = Column(String(255), nullable=False, default="New Chat")
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    # Relationships
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ChatSession(id={self.id}, title='{self.title}', is_active={self.is_active})>"


class ChatMessage(Base):
    """Chat message model for storing individual messages in conversations"""
    
    __tablename__ = "chat_messages"
    
    id = Column(BigInteger, primary_key=True, default=generate_id)
    session_id = Column(BigInteger, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False, index=True)  # user, assistant, system
    content = Column(Text, nullable=False)
    sources = Column(JSON, nullable=True)  # JSON array of source document references
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    session = relationship("ChatSession", back_populates="messages")
    
    def __repr__(self):
        return f"<ChatMessage(id={self.id}, session_id={self.session_id}, role='{self.role}')>"