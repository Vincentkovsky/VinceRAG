"""
Document schemas
"""

from pydantic import BaseModel, HttpUrl, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class DocumentType(str, Enum):
    """Document type enumeration"""
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    MD = "md"
    PPTX = "pptx"
    XLSX = "xlsx"
    CSV = "csv"
    RTF = "rtf"
    URL = "url"


class DocumentStatus(str, Enum):
    """Document processing status"""
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentBase(BaseModel):
    """Base document schema"""
    name: str
    type: DocumentType


class DocumentCreate(DocumentBase):
    """Document creation schema"""
    size: Optional[int] = None  # Will be stored in metadata.fileSize
    url: Optional[HttpUrl] = None  # Will be stored in metadata.url
    metadata: Optional[Dict[str, Any]] = None


class DocumentUpdate(BaseModel):
    """Document update schema"""
    name: Optional[str] = None
    status: Optional[DocumentStatus] = None
    metadata: Optional[Dict[str, Any]] = None


class Document(DocumentBase):
    """Document response schema"""
    id: int  # Snowflake ID
    status: DocumentStatus
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Computed properties from metadata
    @property
    def size(self) -> Optional[int]:
        """Get file size from metadata"""
        return self.metadata.get('fileSize') or self.metadata.get('size')
    
    @property
    def url(self) -> Optional[str]:
        """Get URL from metadata"""
        return self.metadata.get('url')
    
    model_config = {"from_attributes": True}


class DocumentChunkBase(BaseModel):
    """Base document chunk schema"""
    chunk_index: int
    content: str
    start_char: int
    end_char: int
    token_count: int


class DocumentChunk(DocumentChunkBase):
    """Document chunk response schema"""
    id: int  # Snowflake ID
    document_id: int  # Snowflake ID
    vector_id: str
    created_at: datetime
    
    # Optional computed properties
    document_name: Optional[str] = None
    document_type: Optional[str] = None
    similarity: Optional[float] = None
    
    model_config = {"from_attributes": True}


class CrawlOptions(BaseModel):
    """Web crawling options"""
    max_depth: int = 2
    max_pages: int = 10
    include_subdomains: bool = False
    
    @validator('max_depth')
    def validate_max_depth(cls, v):
        if v < 1 or v > 5:
            raise ValueError('Max depth must be between 1 and 5')
        return v
    
    @validator('max_pages')
    def validate_max_pages(cls, v):
        if v < 1 or v > 50:
            raise ValueError('Max pages must be between 1 and 50')
        return v


class URLRequest(BaseModel):
    """URL scraping request"""
    url: HttpUrl
    crawl_options: Optional[CrawlOptions] = None
    
    @validator('url')
    def validate_url_safety(cls, v):
        """Validate URL safety"""
        url_str = str(v).lower()
        dangerous_patterns = ['javascript:', 'data:', 'file:', 'localhost', '127.0.0.1']
        
        if any(pattern in url_str for pattern in dangerous_patterns):
            raise ValueError('Potentially malicious URL detected')
        return v


class DocumentList(BaseModel):
    """Document list response"""
    documents: List[Document]
    total: int
    page: int = 1
    page_size: int = 20


class DocumentChunkList(BaseModel):
    """Document chunk list response"""
    chunks: List[DocumentChunk]
    total: int
    page: int = 1
    page_size: int = 20


class ProcessingStatus(BaseModel):
    """Document processing status"""
    document_id: int
    status: DocumentStatus
    progress: Optional[float] = None  # 0.0 to 1.0
    message: Optional[str] = None
    updated_at: datetime