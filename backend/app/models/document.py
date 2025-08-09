"""
Document and DocumentChunk models
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional

from ..core.database import Base
from ..core.snowflake import generate_id


class Document(Base):
    """Document model for storing uploaded files and web pages"""
    
    __tablename__ = "documents"
    
    id = Column(BigInteger, primary_key=True, default=generate_id)
    name = Column(String(255), nullable=False, index=True)
    type = Column(String(50), nullable=False, index=True)  # pdf, docx, txt, md, pptx, xlsx, csv, rtf, url
    status = Column(String(50), nullable=False, default="processing", index=True)  # processing, completed, failed
    document_metadata = Column(JSON, nullable=False, default=lambda: {})  # Document metadata as JSON
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    # Relationships
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    
    @property
    def size(self) -> Optional[int]:
        """Get file size from metadata"""
        return self.document_metadata.get('fileSize') if self.document_metadata else None
    
    @property
    def url(self) -> Optional[str]:
        """Get URL from metadata"""
        return self.document_metadata.get('url') if self.document_metadata else None
    

    
    def __repr__(self):
        return f"<Document(id={self.id}, name='{self.name}', type='{self.type}', status='{self.status}')>"


class DocumentChunk(Base):
    """Document chunk model for storing text chunks with vector references"""
    
    __tablename__ = "document_chunks"
    
    id = Column(BigInteger, primary_key=True, default=generate_id)
    document_id = Column(BigInteger, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)  # Position within document (0-based)
    vector_id = Column(String(255), nullable=False, unique=True, index=True)  # Reference to vector database
    content = Column(Text, nullable=False)  # Full text content of the chunk
    start_char = Column(Integer, nullable=False)  # Start character position in original document
    end_char = Column(Integer, nullable=False)  # End character position in original document
    token_count = Column(Integer, nullable=False)  # Number of tokens in this chunk
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    document = relationship("Document", back_populates="chunks")
    
    def __repr__(self):
        return f"<DocumentChunk(id={self.id}, document_id={self.document_id}, chunk_index={self.chunk_index})>"