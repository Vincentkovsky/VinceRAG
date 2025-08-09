"""
Tests for database models
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from app.core.database import Base
from app.models.document import Document, DocumentChunk
from app.models.chat import ChatSession, ChatMessage


# Test database setup
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture
async def async_session():
    """Create async test database session"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        yield session
    
    await engine.dispose()


class TestDocumentModel:
    """Test cases for Document model"""
    
    async def test_create_document(self, async_session):
        """Test creating a document"""
        document = Document(
            name="test.pdf",
            type="pdf",
            status="processing",
            metadata={"fileSize": 1024, "mimeType": "application/pdf"}
        )
        
        async_session.add(document)
        await async_session.commit()
        await async_session.refresh(document)
        
        assert document.id is not None
        assert document.name == "test.pdf"
        assert document.type == "pdf"
        assert document.size == 1024  # Accessed via property
        assert document.status == "processing"
        assert document.created_at is not None
        assert document.metadata["fileSize"] == 1024
    
    async def test_document_with_url(self, async_session):
        """Test creating a document with URL"""
        document = Document(
            name="Web Page",
            type="url",
            status="completed",
            metadata={
                "url": "https://example.com",
                "title": "Example Page",
                "scrapedAt": "2024-01-15T10:30:00Z"
            }
        )
        
        async_session.add(document)
        await async_session.commit()
        await async_session.refresh(document)
        
        assert document.url == "https://example.com"  # Accessed via property
        assert document.size is None  # No fileSize in metadata
        assert document.metadata["url"] == "https://example.com"
    
    async def test_document_with_metadata(self, async_session):
        """Test creating a document with metadata"""
        metadata = {"author": "John Doe", "pages": 10}
        document = Document(
            name="test.pdf",
            type="pdf",
            metadata=metadata,
            status="completed"
        )
        
        async_session.add(document)
        await async_session.commit()
        await async_session.refresh(document)
        
        assert document.metadata == metadata


class TestDocumentChunkModel:
    """Test cases for DocumentChunk model"""
    
    async def test_create_document_chunk(self, async_session):
        """Test creating a document chunk"""
        # First create a document
        document = Document(
            name="test.pdf",
            type="pdf",
            status="processing"
        )
        async_session.add(document)
        await async_session.commit()
        await async_session.refresh(document)
        
        # Create a chunk
        chunk = DocumentChunk(
            document_id=document.id,
            chunk_index=0,
            vector_id="vec_123",
            content="This is test content",
            start_char=0,
            end_char=20,
            token_count=5
        )
        
        async_session.add(chunk)
        await async_session.commit()
        await async_session.refresh(chunk)
        
        assert chunk.id is not None
        assert chunk.document_id == document.id
        assert chunk.chunk_index == 0
        assert chunk.vector_id == "vec_123"
        assert chunk.content == "This is test content"
        assert chunk.token_count == 5
    
    async def test_document_chunk_relationship(self, async_session):
        """Test relationship between document and chunks"""
        # Create document
        document = Document(
            name="test.pdf",
            type="pdf",
            status="processing"
        )
        async_session.add(document)
        await async_session.commit()
        await async_session.refresh(document)
        
        # Create chunks
        chunk1 = DocumentChunk(
            document_id=document.id,
            chunk_index=0,
            vector_id="vec_1",
            content="First chunk",
            start_char=0,
            end_char=11,
            token_count=2
        )
        chunk2 = DocumentChunk(
            document_id=document.id,
            chunk_index=1,
            vector_id="vec_2",
            content="Second chunk",
            start_char=12,
            end_char=24,
            token_count=2
        )
        
        async_session.add_all([chunk1, chunk2])
        await async_session.commit()
        
        # Refresh and check relationships
        await async_session.refresh(document)
        assert len(document.chunks) == 2


class TestChatSessionModel:
    """Test cases for ChatSession model"""
    
    async def test_create_chat_session(self, async_session):
        """Test creating a chat session"""
        session = ChatSession(title="Test Chat")
        
        async_session.add(session)
        await async_session.commit()
        await async_session.refresh(session)
        
        assert session.id is not None
        assert session.title == "Test Chat"
        assert session.is_active is True
        assert session.created_at is not None
    
    async def test_chat_session_default_values(self, async_session):
        """Test chat session default values"""
        session = ChatSession()
        
        async_session.add(session)
        await async_session.commit()
        await async_session.refresh(session)
        
        assert session.title == "New Chat"
        assert session.is_active is True


class TestChatMessageModel:
    """Test cases for ChatMessage model"""
    
    async def test_create_chat_message(self, async_session):
        """Test creating a chat message"""
        # First create a session
        session = ChatSession(title="Test Chat")
        async_session.add(session)
        await async_session.commit()
        await async_session.refresh(session)
        
        # Create a message
        message = ChatMessage(
            session_id=session.id,
            role="user",
            content="Hello, how are you?"
        )
        
        async_session.add(message)
        await async_session.commit()
        await async_session.refresh(message)
        
        assert message.id is not None
        assert message.session_id == session.id
        assert message.role == "user"
        assert message.content == "Hello, how are you?"
        assert message.created_at is not None
    
    async def test_chat_message_with_sources(self, async_session):
        """Test creating a chat message with sources"""
        # Create session
        session = ChatSession(title="Test Chat")
        async_session.add(session)
        await async_session.commit()
        await async_session.refresh(session)
        
        # Create message with sources
        sources = '{"documents": ["doc1", "doc2"]}'
        message = ChatMessage(
            session_id=session.id,
            role="assistant",
            content="Based on the documents...",
            sources=sources
        )
        
        async_session.add(message)
        await async_session.commit()
        await async_session.refresh(message)
        
        assert message.sources == sources
    
    async def test_chat_session_message_relationship(self, async_session):
        """Test relationship between session and messages"""
        # Create session
        session = ChatSession(title="Test Chat")
        async_session.add(session)
        await async_session.commit()
        await async_session.refresh(session)
        
        # Create messages
        msg1 = ChatMessage(
            session_id=session.id,
            role="user",
            content="First message"
        )
        msg2 = ChatMessage(
            session_id=session.id,
            role="assistant",
            content="Second message"
        )
        
        async_session.add_all([msg1, msg2])
        await async_session.commit()
        
        # Refresh and check relationships
        await async_session.refresh(session)
        assert len(session.messages) == 2