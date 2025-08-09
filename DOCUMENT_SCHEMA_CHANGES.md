# Document Schema Changes - Removing Field Duplication

## Overview

This document outlines the changes made to eliminate field duplication between the `Document` interface and `DocumentMetadata` in the RAG system design.

## Problem

The original design had duplicate fields:
- `size` field existed both in `Document` interface and as `fileSize` in `FileMetadata`
- `url` field existed both in `Document` interface and as `url` in `WebMetadata`

This duplication created inconsistency and potential data synchronization issues.

## Solution

### 1. Updated Document Interface (TypeScript)

**Before:**
```typescript
interface Document {
  id: number
  name: string
  type: 'pdf' | 'docx' | 'txt' | 'md' | 'pptx' | 'xlsx' | 'csv' | 'rtf' | 'url'
  size?: number        // DUPLICATE
  url?: string         // DUPLICATE
  status: 'processing' | 'completed' | 'failed'
  createdAt: Date
  updatedAt?: Date
  metadata: DocumentMetadata
}
```

**After:**
```typescript
interface Document {
  id: number
  name: string
  type: 'pdf' | 'docx' | 'txt' | 'md' | 'pptx' | 'xlsx' | 'csv' | 'rtf' | 'url'
  status: 'processing' | 'completed' | 'failed'
  createdAt: Date
  updatedAt?: Date
  metadata: DocumentMetadata
  // size and url are now accessed via computed properties from metadata
}
```

### 2. Updated Database Schema

**Before:**
```sql
CREATE TABLE documents (
    id BIGINT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,
    size INTEGER,           -- DUPLICATE
    url TEXT,              -- DUPLICATE
    status VARCHAR(50) NOT NULL DEFAULT 'processing',
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);
```

**After:**
```sql
CREATE TABLE documents (
    id BIGINT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'processing',
    metadata JSONB NOT NULL DEFAULT '{}',  -- Contains fileSize, url, etc.
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);
```

### 3. Updated SQLAlchemy Model

```python
class Document(Base):
    __tablename__ = "documents"
    
    id = Column(BigInteger, primary_key=True, default=generate_id)
    name = Column(String(255), nullable=False, index=True)
    type = Column(String(50), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="processing", index=True)
    metadata = Column(JSON, nullable=False, default=lambda: {})
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    @property
    def size(self) -> Optional[int]:
        """Get file size from metadata"""
        return self.metadata.get('fileSize') if self.metadata else None
    
    @property
    def url(self) -> Optional[str]:
        """Get URL from metadata"""
        return self.metadata.get('url') if self.metadata else None
```

### 4. Updated Pydantic Schemas

```python
class Document(DocumentBase):
    id: int
    status: DocumentStatus
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    @property
    def size(self) -> Optional[int]:
        """Get file size from metadata"""
        return self.metadata.get('fileSize') or self.metadata.get('size')
    
    @property
    def url(self) -> Optional[str]:
        """Get URL from metadata"""
        return self.metadata.get('url')
    
    model_config = {"from_attributes": True}
```

### 5. Service Layer Implementation

Created `DocumentService` to handle the data transformation:

```python
@staticmethod
def _prepare_metadata(document_data: DocumentCreate) -> Dict[str, Any]:
    """Prepare metadata from document creation data"""
    metadata = document_data.metadata or {}
    
    # Move size to metadata.fileSize if provided
    if document_data.size is not None:
        metadata['fileSize'] = document_data.size
    
    # Move url to metadata.url if provided
    if document_data.url is not None:
        metadata['url'] = str(document_data.url)
    
    return metadata
```

## Benefits

1. **Eliminates Data Duplication**: No more conflicting values between direct fields and metadata
2. **Flexible Metadata**: All document-specific information is stored in a structured metadata JSON
3. **Backward Compatibility**: Properties provide access to size/url for existing code
4. **Type Safety**: Pydantic schemas ensure proper validation and serialization
5. **Consistent API**: API responses remain the same through computed properties

## Migration

A database migration (`0002_remove_duplicate_fields.py`) was created to:
1. Remove the `size` and `url` columns from the documents table
2. Migrate existing data to the metadata JSON field
3. Ensure no data loss during the transition

## Testing

Updated all tests to:
- Use metadata-based document creation
- Test property access for size and url
- Verify service layer functionality
- Ensure API endpoints work correctly

## Files Modified

- `.kiro/specs/langchain-rag-system/design.md` - Updated Document interface and API examples
- `backend/app/models/document.py` - Removed duplicate fields, added properties
- `backend/app/schemas/document.py` - Updated Pydantic schemas with properties
- `backend/app/services/document_service.py` - Created service layer for data handling
- `backend/app/api/v1/documents.py` - Updated API endpoints to use service layer
- `backend/alembic/versions/0002_remove_duplicate_fields.py` - Database migration
- `backend/tests/test_models.py` - Updated model tests
- `backend/tests/test_document_service.py` - Created service layer tests

This refactoring provides a cleaner, more maintainable architecture while preserving all existing functionality.