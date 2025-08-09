"""Document service for handling document operations"""

from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from ..models.document import Document
from ..schemas.document import DocumentCreate, DocumentUpdate
from ..core.snowflake import generate_id


class DocumentService:
    """Service for document operations"""
    
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
        
        # Add other type-specific metadata
        if document_data.type == 'url':
            # For URL documents, ensure we have web metadata structure
            if 'scrapedAt' not in metadata:
                from datetime import datetime
                metadata['scrapedAt'] = datetime.utcnow().isoformat()
        else:
            # For file documents, ensure we have file metadata structure
            if 'originalFileName' not in metadata and document_data.name:
                metadata['originalFileName'] = document_data.name
        
        return metadata
    
    @staticmethod
    async def create_document(
        db: AsyncSession, 
        document_data: DocumentCreate
    ) -> Document:
        """Create a new document"""
        
        # Prepare metadata
        metadata = DocumentService._prepare_metadata(document_data)
        
        # Create document instance
        document = Document(
            id=generate_id(),
            name=document_data.name,
            type=document_data.type,
            status="processing",
            document_metadata=metadata
        )
        
        db.add(document)
        await db.commit()
        await db.refresh(document)
        
        return document
    
    @staticmethod
    async def get_document(db: AsyncSession, document_id: int) -> Optional[Document]:
        """Get document by ID"""
        result = await db.execute(
            select(Document).where(Document.id == document_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def list_documents(
        db: AsyncSession, 
        skip: int = 0, 
        limit: int = 20
    ) -> tuple[List[Document], int]:
        """List documents with pagination"""
        # Get total count
        count_result = await db.execute(select(func.count(Document.id)))
        total = count_result.scalar()
        
        # Get documents
        result = await db.execute(
            select(Document)
            .order_by(Document.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        documents = result.scalars().all()
        
        return list(documents), total
    
    @staticmethod
    async def update_document(
        db: AsyncSession, 
        document_id: int, 
        update_data: DocumentUpdate
    ) -> Optional[Document]:
        """Update document"""
        document = await DocumentService.get_document(db, document_id)
        if not document:
            return None
        
        # Update fields
        if update_data.name is not None:
            document.name = update_data.name
        
        if update_data.status is not None:
            document.status = update_data.status
        
        if update_data.metadata is not None:
            # Merge metadata
            current_metadata = document.document_metadata or {}
            current_metadata.update(update_data.metadata)
            document.document_metadata = current_metadata
        
        await db.commit()
        await db.refresh(document)
        
        return document
    
    @staticmethod
    async def delete_document(db: AsyncSession, document_id: int) -> bool:
        """Delete document"""
        document = await DocumentService.get_document(db, document_id)
        if not document:
            return False
        
        await db.delete(document)
        await db.commit()
        
        return True
    
    @staticmethod
    async def get_document_with_chunks(
        db: AsyncSession, 
        document_id: int
    ) -> Optional[Document]:
        """Get document with its chunks"""
        result = await db.execute(
            select(Document)
            .options(selectinload(Document.chunks))
            .where(Document.id == document_id)
        )
        return result.scalar_one_or_none()