"""
Chat schemas
"""

from pydantic import BaseModel, ConfigDict, field_validator, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    """Chat message role"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class DocumentSource(BaseModel):
    """Document source reference in chat response"""
    chunk_id: int  # DocumentChunk.id (Snowflake ID)
    document_id: int  # Document.id (Snowflake ID)
    document_name: str  # Document.name with icon
    document_type: str  # Document.type
    
    # Content and relevance
    chunk: str  # DocumentChunk.content (truncated for display)
    similarity: float  # Similarity score from vector search
    chunk_index: int  # DocumentChunk.chunk_index
    
    # Position information
    start_char: int  # DocumentChunk.start_char
    end_char: int  # DocumentChunk.end_char
    token_count: int  # DocumentChunk.token_count
    
    # Document metadata (optional)
    url: Optional[str] = None
    mime_type: Optional[str] = None
    author: Optional[str] = None
    published_date: Optional[datetime] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    domain: Optional[str] = None
    language: Optional[str] = None
    
    # Display helpers
    context_info: Optional[List[str]] = None
    highlighted: Optional[str] = None


class ChatMessageBase(BaseModel):
    """Base chat message schema"""
    role: MessageRole
    content: str


class ChatMessageCreate(ChatMessageBase):
    """Chat message creation schema"""
    session_id: Optional[int] = None  # Snowflake ID


class ChatMessage(ChatMessageBase):
    """Chat message response schema"""
    id: int  # Snowflake ID
    session_id: int  # Snowflake ID
    sources: Optional[List[DocumentSource]] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ChatSessionBase(BaseModel):
    """Base chat session schema"""
    title: str = "New Chat"


class ChatSessionCreate(ChatSessionBase):
    """Chat session creation schema"""
    pass


class ChatSessionUpdate(BaseModel):
    """Chat session update schema"""
    title: Optional[str] = None
    is_active: Optional[bool] = None


class ChatSession(ChatSessionBase):
    """Chat session response schema"""
    id: int  # Snowflake ID
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Optional message count
    message_count: Optional[int] = None
    last_message_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class ChatQuery(BaseModel):
    """Chat query request"""
    query: str
    session_id: Optional[int] = None  # Snowflake ID
    
    @field_validator('query')
    @classmethod
    def validate_query(cls, v):
        if not v or not v.strip():
            raise ValueError('Query cannot be empty')
        if len(v.strip()) > 4000:
            raise ValueError('Query too long (max 4000 characters)')
        return v.strip()


class ChatResponse(BaseModel):
    """Chat response"""
    answer: str
    sources: List[DocumentSource]
    confidence: Optional[float] = None
    session_id: int  # Snowflake ID
    message_id: int  # Snowflake ID


class ChatSessionList(BaseModel):
    """Chat session list response"""
    sessions: List[ChatSession]
    total: int
    page: int = 1
    page_size: int = 20


class ChatMessageList(BaseModel):
    """Chat message list response"""
    messages: List[ChatMessage]
    total: int
    page: int = 1
    page_size: int = 20
    session: Optional[ChatSession] = None