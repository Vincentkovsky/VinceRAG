"""
Pydantic schemas package
"""

from .auth import UserBase, UserCreate, UserLogin, User, Token, TokenData
from .document import (
    DocumentType, DocumentStatus, DocumentBase, DocumentCreate, 
    DocumentUpdate, Document, DocumentChunk, CrawlOptions, 
    URLRequest, DocumentList, ProcessingStatus
)
from .chat import (
    MessageRole, DocumentSource, ChatMessageBase, ChatMessageCreate,
    ChatMessage, ChatSessionBase, ChatSessionCreate, ChatSessionUpdate,
    ChatSession, ChatQuery, ChatResponse, ChatSessionList, ChatMessageList
)

__all__ = [
    # Auth schemas
    "UserBase", "UserCreate", "UserLogin", "User", "Token", "TokenData",
    
    # Document schemas
    "DocumentType", "DocumentStatus", "DocumentBase", "DocumentCreate", 
    "DocumentUpdate", "Document", "DocumentChunk", "CrawlOptions", 
    "URLRequest", "DocumentList", "ProcessingStatus",
    
    # Chat schemas
    "MessageRole", "DocumentSource", "ChatMessageBase", "ChatMessageCreate",
    "ChatMessage", "ChatSessionBase", "ChatSessionCreate", "ChatSessionUpdate",
    "ChatSession", "ChatQuery", "ChatResponse", "ChatSessionList", "ChatMessageList"
]