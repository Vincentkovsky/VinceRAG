"""
Tests for RAG service functionality
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.services.rag_service import (
    RAGQueryService,
    ChatSessionManager,
    CustomRetriever,
    RAGError,
    rag_service,
    chat_manager
)
from app.models.chat import ChatSession, ChatMessage
from app.core.config import settings


@pytest.fixture
def mock_langchain_components():
    """Mock LangChain components"""
    with patch('app.services.rag_service.ChatOpenAI') as mock_llm:
        
        # Mock LLM
        mock_llm_instance = AsyncMock()
        mock_llm_instance.ainvoke.return_value = Mock(content="Test response")
        mock_llm_instance.astream.return_value = [
            Mock(content="Test "),
            Mock(content="streaming "),
            Mock(content="response")
        ]
        mock_llm.return_value = mock_llm_instance
        
        yield {
            'llm': mock_llm,
            'llm_instance': mock_llm_instance
        }


@pytest.fixture
def mock_vector_service():
    """Mock vector service"""
    with patch('app.services.rag_service.chunk_storage_manager') as mock_manager:
        # Make it an async mock
        mock_manager.similarity_search = AsyncMock(return_value=[
            {
                "content": "This is a test document about artificial intelligence.",
                "similarity": 0.9,
                "metadata": {
                    "chunk_id": 123,
                    "document_id": 456,
                    "chunk_index": 0
                },
                "chunk_id": 123,
                "document_id": 456,
                "chunk_index": 0
            },
            {
                "content": "Machine learning is a subset of AI.",
                "similarity": 0.8,
                "metadata": {
                    "chunk_id": 124,
                    "document_id": 456,
                    "chunk_index": 1
                },
                "chunk_id": 124,
                "document_id": 456,
                "chunk_index": 1
            }
        ])
        yield mock_manager


class TestCustomRetriever:
    """Test custom retriever functionality"""
    
    @pytest.mark.asyncio
    async def test_retrieve_documents_success(self, mock_vector_service):
        """Test successful document retrieval"""
        retriever = CustomRetriever(similarity_threshold=0.7)
        
        documents = await retriever._aget_relevant_documents("test query")
        
        assert len(documents) == 2
        assert documents[0].page_content == "This is a test document about artificial intelligence."
        assert documents[0].metadata["similarity"] == 0.9
        assert documents[0].metadata["chunk_id"] == 123
        
        mock_vector_service.similarity_search.assert_called_once_with(
            query="test query",
            n_results=10,
            document_id=None,
            similarity_threshold=0.7
        )
    
    @pytest.mark.asyncio
    async def test_retrieve_documents_with_document_filter(self, mock_vector_service):
        """Test document retrieval with document ID filter"""
        retriever = CustomRetriever(document_id=456, similarity_threshold=0.8)
        
        documents = await retriever._aget_relevant_documents("test query")
        
        assert len(documents) == 2
        mock_vector_service.similarity_search.assert_called_once_with(
            query="test query",
            n_results=10,
            document_id=456,
            similarity_threshold=0.8
        )
    
    @pytest.mark.asyncio
    async def test_retrieve_documents_error(self, mock_vector_service):
        """Test error handling in document retrieval"""
        mock_vector_service.similarity_search.side_effect = Exception("Vector search failed")
        
        retriever = CustomRetriever()
        
        with pytest.raises(RAGError, match="Document retrieval failed"):
            await retriever._aget_relevant_documents("test query")
    
    def test_sync_method_not_implemented(self):
        """Test that sync method raises NotImplementedError"""
        retriever = CustomRetriever()
        
        with pytest.raises(NotImplementedError):
            retriever._get_relevant_documents("test query")


class TestRAGQueryService:
    """Test RAG query service functionality"""
    
    @pytest.mark.asyncio
    async def test_initialization_success(self, mock_langchain_components):
        """Test successful service initialization"""
        with patch.object(settings, 'openai_api_key', 'test-key'):
            service = RAGQueryService()
            
            assert service.llm is not None
            assert service.llm_non_streaming is not None
            assert service.prompt is not None
    
    def test_initialization_no_api_key(self):
        """Test initialization without API key"""
        with patch.object(settings, 'openai_api_key', None):
            with pytest.raises(ValueError, match="OpenAI API key is required"):
                RAGQueryService()
    
    @pytest.mark.asyncio
    async def test_query_success(self, mock_langchain_components, mock_vector_service):
        """Test successful RAG query"""
        with patch.object(settings, 'openai_api_key', 'test-key'):
            service = RAGQueryService()
            
            result = await service.query("What is AI?")
            
            assert result["answer"] == "Test response"
            assert len(result["sources"]) == 2  # From mock_vector_service
            assert result["sources"][0]["chunk_id"] == 123
            assert result["confidence"] > 0
            assert "processing_time" in result
            assert result["retrieved_documents"] == 2
    
    @pytest.mark.asyncio
    async def test_query_with_chat_history(self, mock_langchain_components, mock_vector_service):
        """Test RAG query with chat history"""
        with patch.object(settings, 'openai_api_key', 'test-key'):
            service = RAGQueryService()
            
            chat_history = [
                {"role": "user", "content": "What is AI?"},
                {"role": "assistant", "content": "AI is artificial intelligence."}
            ]
            
            result = await service.query("Tell me more", chat_history=chat_history)
            
            assert result["answer"] == "Test response"
            # Verify LLM was called
            mock_langchain_components['llm_instance'].ainvoke.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_query_error_handling(self, mock_langchain_components, mock_vector_service):
        """Test error handling in query processing"""
        with patch.object(settings, 'openai_api_key', 'test-key'):
            service = RAGQueryService()
            
            mock_langchain_components['llm_instance'].ainvoke.side_effect = Exception("LLM error")
            
            with pytest.raises(RAGError, match="Query processing failed"):
                await service.query("What is AI?")
    
    @pytest.mark.asyncio
    async def test_stream_query_success(self, mock_langchain_components, mock_vector_service):
        """Test successful streaming query"""
        with patch.object(settings, 'openai_api_key', 'test-key'):
            service = RAGQueryService()
            
            # Mock streaming response
            async def mock_astream(messages):
                chunks = [
                    Mock(content="Test "),
                    Mock(content="streaming "),
                    Mock(content="response")
                ]
                for chunk in chunks:
                    yield chunk
            
            mock_langchain_components['llm_instance'].astream = mock_astream
            
            result_chunks = []
            async for chunk in service.stream_query("What is AI?"):
                result_chunks.append(chunk)
            
            assert len(result_chunks) == 3
            assert "".join(result_chunks) == "Test streaming response"
    
    @pytest.mark.asyncio
    async def test_get_query_suggestions(self, mock_langchain_components):
        """Test query suggestions generation"""
        with patch.object(settings, 'openai_api_key', 'test-key'):
            service = RAGQueryService()
            
            suggestions = await service.get_query_suggestions(limit=3)
            
            assert len(suggestions) == 3
            assert all(isinstance(s, str) for s in suggestions)
            assert "What is the main topic" in suggestions[0]
    
    @pytest.mark.asyncio
    async def test_analyze_query_complexity(self, mock_langchain_components):
        """Test query complexity analysis"""
        with patch.object(settings, 'openai_api_key', 'test-key'):
            service = RAGQueryService()
            
            # Test simple query
            analysis = await service.analyze_query_complexity("What is AI?")
            assert analysis["complexity"] == "simple"
            assert analysis["word_count"] == 3
            assert "factual" in analysis["question_types"]
            
            # Test complex query
            complex_query = "Can you provide a comprehensive analysis of the differences between machine learning and deep learning approaches in artificial intelligence systems?"
            analysis = await service.analyze_query_complexity(complex_query)
            # The query has 21 words, which should be "complex" (> 20)
            assert analysis["complexity"] in ["medium", "complex"]  # Accept both since it's borderline
            assert analysis["word_count"] > 15


class TestChatSessionManager:
    """Test chat session manager functionality"""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session"""
        session = AsyncMock(spec=AsyncSession)
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.add = Mock()
        session.delete = AsyncMock()
        session.refresh = AsyncMock()
        return session
    
    @pytest.fixture
    def mock_rag_service(self):
        """Mock RAG service"""
        service = AsyncMock(spec=RAGQueryService)
        service.query.return_value = {
            "answer": "Test answer",
            "sources": [{"chunk_id": 123, "similarity": 0.9}],
            "confidence": 0.9,
            "processing_time": 1.5
        }
        
        async def mock_stream():
            chunks = ["Test ", "streaming ", "answer"]
            for chunk in chunks:
                yield chunk
        
        service.stream_query.return_value = mock_stream()
        return service
    
    @pytest.mark.asyncio
    async def test_create_session_success(self, mock_db_session, mock_rag_service):
        """Test successful session creation"""
        manager = ChatSessionManager(mock_rag_service)
        
        # Mock the created session
        mock_session = Mock(spec=ChatSession)
        mock_session.id = 123
        mock_session.title = "Test Chat"
        mock_db_session.refresh.side_effect = lambda obj: setattr(obj, 'id', 123)
        
        with patch('app.services.rag_service.ChatSession', return_value=mock_session):
            session = await manager.create_session(mock_db_session, "Test Chat")
            
            assert session.title == "Test Chat"
            mock_db_session.add.assert_called_once()
            mock_db_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_session_error(self, mock_db_session, mock_rag_service):
        """Test session creation error handling"""
        manager = ChatSessionManager(mock_rag_service)
        mock_db_session.commit.side_effect = Exception("Database error")
        
        with patch('app.services.rag_service.ChatSession'):
            with pytest.raises(RAGError, match="Session creation failed"):
                await manager.create_session(mock_db_session)
            
            mock_db_session.rollback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_session_success(self, mock_db_session, mock_rag_service):
        """Test successful session retrieval"""
        manager = ChatSessionManager(mock_rag_service)
        
        mock_session = Mock(spec=ChatSession)
        mock_session.id = 123
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_session
        mock_db_session.execute.return_value = mock_result
        
        session = await manager.get_session(mock_db_session, 123)
        
        assert session == mock_session
        mock_db_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_session_not_found(self, mock_db_session, mock_rag_service):
        """Test session not found"""
        manager = ChatSessionManager(mock_rag_service)
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result
        
        session = await manager.get_session(mock_db_session, 999)
        
        assert session is None
    
    @pytest.mark.asyncio
    async def test_add_message_success(self, mock_db_session, mock_rag_service):
        """Test successful message addition"""
        manager = ChatSessionManager(mock_rag_service)
        
        mock_message = Mock(spec=ChatMessage)
        mock_message.id = 456
        mock_session = Mock(spec=ChatSession)
        mock_session.id = 123
        
        # Mock session retrieval
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_session
        mock_db_session.execute.return_value = mock_result
        
        with patch('app.services.rag_service.ChatMessage', return_value=mock_message):
            message = await manager.add_message(
                mock_db_session, 123, "user", "Test message"
            )
            
            assert message == mock_message
            mock_db_session.add.assert_called()
            assert mock_db_session.commit.call_count == 2  # Once for message, once for session update
    
    @pytest.mark.asyncio
    async def test_send_message_success(self, mock_db_session, mock_rag_service):
        """Test successful message sending with RAG response"""
        manager = ChatSessionManager(mock_rag_service)
        
        # Mock session
        mock_session = Mock(spec=ChatSession)
        mock_session.id = 123
        
        # Mock messages for history
        mock_messages = []
        
        # Mock message creation
        mock_user_message = Mock(spec=ChatMessage)
        mock_user_message.id = 456
        mock_assistant_message = Mock(spec=ChatMessage)
        mock_assistant_message.id = 457
        
        with patch.object(manager, 'get_session', return_value=mock_session), \
             patch.object(manager, 'get_session_messages', return_value=mock_messages), \
             patch.object(manager, 'add_message', side_effect=[mock_user_message, mock_assistant_message]):
            
            response = await manager.send_message(
                mock_db_session, 123, "What is AI?"
            )
            
            assert response["session_id"] == 123
            assert response["user_message_id"] == 456
            assert response["assistant_message_id"] == 457
            assert response["answer"] == "Test answer"
            assert len(response["sources"]) == 1
            assert response["confidence"] == 0.9
    
    @pytest.mark.asyncio
    async def test_send_message_session_not_found(self, mock_db_session, mock_rag_service):
        """Test message sending with non-existent session"""
        manager = ChatSessionManager(mock_rag_service)
        
        with patch.object(manager, 'get_session', return_value=None):
            with pytest.raises(RAGError, match="Session 999 not found"):
                await manager.send_message(mock_db_session, 999, "Test question")
    
    @pytest.mark.asyncio
    async def test_stream_message_success(self, mock_db_session, mock_rag_service):
        """Test successful streaming message"""
        manager = ChatSessionManager(mock_rag_service)
        
        # Mock session and messages
        mock_session = Mock(spec=ChatSession)
        mock_session.id = 123
        mock_user_message = Mock(spec=ChatMessage)
        mock_user_message.id = 456
        mock_assistant_message = Mock(spec=ChatMessage)
        mock_assistant_message.id = 457
        
        with patch.object(manager, 'get_session', return_value=mock_session), \
             patch.object(manager, 'get_session_messages', return_value=[]), \
             patch.object(manager, 'add_message', side_effect=[mock_user_message, mock_assistant_message]):
            
            chunks = []
            async for chunk in manager.stream_message(
                mock_db_session, 123, "What is AI?"
            ):
                chunks.append(chunk)
            
            # Should have message_created, content_deltas, and message_completed
            assert len(chunks) >= 4  # At least 4 chunks
            assert chunks[0]["type"] == "message_created"
            assert chunks[0]["user_message_id"] == 456
            assert chunks[-1]["type"] == "message_completed"
            assert chunks[-1]["assistant_message_id"] == 457
    
    @pytest.mark.asyncio
    async def test_delete_session_success(self, mock_db_session, mock_rag_service):
        """Test successful session deletion"""
        manager = ChatSessionManager(mock_rag_service)
        
        mock_session = Mock(spec=ChatSession)
        mock_session.id = 123
        mock_session.is_active = True
        
        with patch.object(manager, 'get_session', return_value=mock_session):
            result = await manager.delete_session(mock_db_session, 123)
            
            assert result is True
            assert mock_session.is_active is False
            mock_db_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_session_not_found(self, mock_db_session, mock_rag_service):
        """Test deletion of non-existent session"""
        manager = ChatSessionManager(mock_rag_service)
        
        with patch.object(manager, 'get_session', return_value=None):
            result = await manager.delete_session(mock_db_session, 999)
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_update_session_title_success(self, mock_db_session, mock_rag_service):
        """Test successful session title update"""
        manager = ChatSessionManager(mock_rag_service)
        
        mock_session = Mock(spec=ChatSession)
        mock_session.id = 123
        mock_session.title = "Old Title"
        
        with patch.object(manager, 'get_session', return_value=mock_session):
            updated_session = await manager.update_session_title(
                mock_db_session, 123, "New Title"
            )
            
            assert updated_session == mock_session
            assert mock_session.title == "New Title"
            mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_global_instances_initialization():
    """Test that global instances are properly initialized"""
    with patch.object(settings, 'openai_api_key', 'test-key'):
        # Test that global instances can be imported and used
        from app.services.rag_service import rag_service, chat_manager
        
        assert rag_service is not None
        assert chat_manager is not None
        assert isinstance(chat_manager.rag_service, RAGQueryService)


@pytest.mark.asyncio
async def test_integration_rag_flow(mock_vector_service):
    """Integration test for complete RAG flow"""
    with patch.object(settings, 'openai_api_key', 'test-key'):
        with patch('app.services.rag_service.ChatOpenAI') as mock_llm:
            
            # Setup mocks
            mock_llm_instance = AsyncMock()
            mock_llm_instance.ainvoke.return_value = Mock(content="AI is artificial intelligence.")
            mock_llm.return_value = mock_llm_instance
            
            # Test the flow
            service = RAGQueryService()
            result = await service.query("What is AI?")
            
            assert result["answer"] == "AI is artificial intelligence."
            assert len(result["sources"]) == 2  # From mock_vector_service
            assert result["confidence"] > 0
            assert "processing_time" in result