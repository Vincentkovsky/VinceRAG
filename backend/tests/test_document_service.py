"""Tests for document service"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.document_service import DocumentService
from app.schemas.document import DocumentCreate, DocumentType
from app.models.document import Document


class TestDocumentService:
    """Test cases for DocumentService"""
    
    async def test_create_file_document(self, async_session: AsyncSession):
        """Test creating a file document"""
        document_data = DocumentCreate(
            name="test.pdf",
            type=DocumentType.PDF,
            size=1024,
            metadata={"mimeType": "application/pdf"}
        )
        
        document = await DocumentService.create_document(async_session, document_data)
        
        assert document.id is not None
        assert document.name == "test.pdf"
        assert document.type == "pdf"
        assert document.status == "processing"
        assert document.size == 1024  # Accessed via property
        assert document.metadata["fileSize"] == 1024
        assert document.metadata["originalFileName"] == "test.pdf"
        assert document.metadata["mimeType"] == "application/pdf"
    
    async def test_create_url_document(self, async_session: AsyncSession):
        """Test creating a URL document"""
        from pydantic import HttpUrl
        
        document_data = DocumentCreate(
            name="Example Page",
            type=DocumentType.URL,
            url=HttpUrl("https://example.com"),
            metadata={"title": "Example Page"}
        )
        
        document = await DocumentService.create_document(async_session, document_data)
        
        assert document.id is not None
        assert document.name == "Example Page"
        assert document.type == "url"
        assert document.status == "processing"
        assert document.url == "https://example.com"  # Accessed via property
        assert document.metadata["url"] == "https://example.com"
        assert document.metadata["title"] == "Example Page"
        assert "scrapedAt" in document.metadata
    
    async def test_get_document(self, async_session: AsyncSession):
        """Test getting a document by ID"""
        # Create a document first
        document_data = DocumentCreate(
            name="test.txt",
            type=DocumentType.TXT,
            size=512
        )
        
        created_document = await DocumentService.create_document(async_session, document_data)
        
        # Get the document
        retrieved_document = await DocumentService.get_document(async_session, created_document.id)
        
        assert retrieved_document is not None
        assert retrieved_document.id == created_document.id
        assert retrieved_document.name == "test.txt"
        assert retrieved_document.size == 512
    
    async def test_get_nonexistent_document(self, async_session: AsyncSession):
        """Test getting a non-existent document"""
        document = await DocumentService.get_document(async_session, 999999)
        assert document is None
    
    async def test_list_documents(self, async_session: AsyncSession):
        """Test listing documents with pagination"""
        # Create some documents
        for i in range(5):
            document_data = DocumentCreate(
                name=f"test_{i}.pdf",
                type=DocumentType.PDF,
                size=1024 * (i + 1)
            )
            await DocumentService.create_document(async_session, document_data)
        
        # Test pagination
        documents, total = await DocumentService.list_documents(async_session, skip=0, limit=3)
        
        assert len(documents) == 3
        assert total == 5
        
        # Test second page
        documents, total = await DocumentService.list_documents(async_session, skip=3, limit=3)
        
        assert len(documents) == 2
        assert total == 5
    
    async def test_delete_document(self, async_session: AsyncSession):
        """Test deleting a document"""
        # Create a document first
        document_data = DocumentCreate(
            name="to_delete.pdf",
            type=DocumentType.PDF,
            size=2048
        )
        
        created_document = await DocumentService.create_document(async_session, document_data)
        document_id = created_document.id
        
        # Delete the document
        success = await DocumentService.delete_document(async_session, document_id)
        assert success is True
        
        # Verify it's deleted
        deleted_document = await DocumentService.get_document(async_session, document_id)
        assert deleted_document is None
    
    async def test_delete_nonexistent_document(self, async_session: AsyncSession):
        """Test deleting a non-existent document"""
        success = await DocumentService.delete_document(async_session, 999999)
        assert success is False