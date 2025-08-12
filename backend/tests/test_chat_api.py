"""
Tests for chat API endpoints
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from httpx import AsyncClient
from datetime import datetime

from app.main import app
from app.models.chat import ChatSession, ChatMessage
from app.services.rag_service import RAGError


@pytest.fixture
def mock_chat_manager():
    """Mock chat manager"""
    with patch('app.api.v1.chat.chat_manager') as mock_manager:
        # Mock session
        mock_session = Mock(spec=ChatSession)
        mock_session.id = 123
        mock_session.title = "Test Chat"
        mock_session.is_active = True
        mock_session.created_at = datetime.now()
        mock_session.updated_at = None
        
        # Mock message
        mock_message = Mock(spec=ChatMessage)
        mock_message.id = 456
        mock_message.session_id = 123
        mock_message.role = "user"
        mock_message.content = "Test message"
        mock_message.sources = None
        mock_message.created_at = datetime.now()
        
        # Configure mock methods
        mock_manager.create_session.return_value = mock_session
        mock_manager.get_session.return_value = mock_session
        mock_manager.get_session_messages.return_value = [mock_message]
        mock_manager.send_message.return_value = {
            "session_id": 123,
            "user_message_id": 456,
            "assistant_message_id": 457,
            "answer": "Test answer",
            "sources": [{"chunk_id": 123, "similarity": 0.9}],
            "confidence": 0.9,
            "processing_time": 1.5
        }
        mock_manager.delete_session.return_value = True
        mock_manager.update_session_title.return_value = mock_session
        
        # Mock streaming
        async def mock_stream():
            chunks = [
                {"type": "message_created", "user_message_id": 456, "session_id": 123},
                {"type": "content_delta", "delta": "Test "},
                {"type": "content_delta", "delta": "streaming "},
                {"type": "content_delta", "delta": "answer"},
                {"type": "message_completed", "assistant_message_id": 457, "full_content": "Test streaming answer"}
            ]
            for chunk in chunks:
                yield chunk
        
        mock_manager.stream_message.return_value = mock_stream()
        
        yield mock_manager


@pytest.fixture
def mock_rag_service():
    """Mock RAG service"""
    with patch('app.api.v1.chat.rag_service') as mock_service:
        mock_service.query.return_value = {
            "answer": "Direct query answer",
            "sources": [{"chunk_id": 123, "similarity": 0.9}],
            "confidence": 0.9,
            "processing_time": 1.2,
            "retrieved_documents": 1
        }
        
        async def mock_stream():
            chunks = ["Direct ", "streaming ", "answer"]
            for chunk in chunks:
                yield chunk
        
        mock_service.stream_query.return_value = mock_stream()
        mock_service.get_query_suggestions.return_value = [
            "What is the main topic?",
            "Can you summarize?",
            "What are the key points?"
        ]
        mock_service.analyze_query_complexity.return_value = {
            "complexity": "simple",
            "word_count": 3,
            "question_types": ["factual"],
            "estimated_processing_time": 0.3
        }
        
        yield mock_service


@pytest.fixture
def mock_db_session():
    """Mock database session with chat data"""
    with patch('app.api.v1.chat.get_db') as mock_get_db:
        mock_db = AsyncMock()
        
        # Mock session query results
        mock_sessions = [
            Mock(
                id=123,
                title="Test Chat 1",
                is_active=True,
                created_at=datetime.now(),
                updated_at=None
            ),
            Mock(
                id=124,
                title="Test Chat 2",
                is_active=True,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        ]
        
        # Mock messages
        mock_messages = [
            Mock(id=1, session_id=123),
            Mock(id=2, session_id=123),
            Mock(id=3, session_id=124)
        ]
        
        # Configure execute method for different queries
        def mock_execute(query):
            mock_result = Mock()
            if "chat_sessions" in str(query):
                mock_result.scalars.return_value.all.return_value = mock_sessions
            elif "chat_messages" in str(query):
                # Filter messages by session_id if present
                if "session_id" in str(query):
                    filtered_messages = [msg for msg in mock_messages if msg.session_id == 123]
                    mock_result.scalars.return_value.all.return_value = filtered_messages
                else:
                    mock_result.scalars.return_value.all.return_value = mock_messages
            return mock_result
        
        mock_db.execute.side_effect = mock_execute
        mock_get_db.return_value = mock_db
        
        yield mock_db


@pytest.fixture
def mock_current_user():
    """Mock current user"""
    with patch('app.api.v1.chat.get_current_active_user') as mock_user:
        user = Mock()
        user.id = 1
        user.email = "test@example.com"
        mock_user.return_value = user
        yield user


class TestChatSessionEndpoints:
    """Test chat session management endpoints"""
    
    @pytest.mark.asyncio
    async def test_list_chat_sessions(self, mock_chat_manager, mock_db_session, mock_current_user):
        """Test listing chat sessions"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/chat/sessions")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["id"] == 123
            assert data[0]["title"] == "Test Chat 1"
            assert "message_count" in data[0]
    
    @pytest.mark.asyncio
    async def test_list_chat_sessions_with_pagination(self, mock_chat_manager, mock_db_session, mock_current_user):
        """Test listing chat sessions with pagination"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/chat/sessions?skip=0&limit=1")
            
            assert response.status_code == 200
            data = response.json()
            # Should still return all sessions since mock doesn't implement pagination
            assert len(data) >= 1
    
    @pytest.mark.asyncio
    async def test_create_chat_session(self, mock_chat_manager, mock_db_session, mock_current_user):
        """Test creating a new chat session"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat/sessions",
                json={"title": "New Test Chat"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 123
            assert data["title"] == "Test Chat"
            assert data["is_active"] is True
            assert data["message_count"] == 0
            
            mock_chat_manager.create_session.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_chat_session_without_title(self, mock_chat_manager, mock_db_session, mock_current_user):
        """Test creating a chat session without title"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post("/api/v1/chat/sessions", json={})
            
            assert response.status_code == 200
            mock_chat_manager.create_session.assert_called_once_with(mock_db_session, None)
    
    @pytest.mark.asyncio
    async def test_create_chat_session_error(self, mock_chat_manager, mock_db_session, mock_current_user):
        """Test chat session creation error"""
        mock_chat_manager.create_session.side_effect = RAGError("Creation failed")
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post("/api/v1/chat/sessions", json={})
            
            assert response.status_code == 500
            assert "Creation failed" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_get_chat_session(self, mock_chat_manager, mock_db_session, mock_current_user):
        """Test getting a specific chat session"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/chat/sessions/123")
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 123
            assert data["title"] == "Test Chat"
            assert "message_count" in data
    
    @pytest.mark.asyncio
    async def test_get_chat_session_not_found(self, mock_chat_manager, mock_db_session, mock_current_user):
        """Test getting non-existent chat session"""
        mock_chat_manager.get_session.return_value = None
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/chat/sessions/999")
            
            assert response.status_code == 404
            assert "Session not found" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_update_chat_session(self, mock_chat_manager, mock_db_session, mock_current_user):
        """Test updating a chat session"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.put(
                "/api/v1/chat/sessions/123",
                json={"title": "Updated Title"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 123
            
            mock_chat_manager.update_session_title.assert_called_once_with(
                mock_db_session, 123, "Updated Title"
            )
    
    @pytest.mark.asyncio
    async def test_update_chat_session_without_title(self, mock_chat_manager, mock_db_session, mock_current_user):
        """Test updating session without title"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.put("/api/v1/chat/sessions/123", json={})
            
            assert response.status_code == 400
            assert "Title is required" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_update_chat_session_not_found(self, mock_chat_manager, mock_db_session, mock_current_user):
        """Test updating non-existent session"""
        mock_chat_manager.update_session_title.return_value = None
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.put(
                "/api/v1/chat/sessions/999",
                json={"title": "New Title"}
            )
            
            assert response.status_code == 404
            assert "Session not found" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_delete_chat_session(self, mock_chat_manager, mock_db_session, mock_current_user):
        """Test deleting a chat session"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.delete("/api/v1/chat/sessions/123")
            
            assert response.status_code == 200
            assert "deleted successfully" in response.json()["message"]
            
            mock_chat_manager.delete_session.assert_called_once_with(mock_db_session, 123)
    
    @pytest.mark.asyncio
    async def test_delete_chat_session_not_found(self, mock_chat_manager, mock_db_session, mock_current_user):
        """Test deleting non-existent session"""
        mock_chat_manager.delete_session.return_value = False
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.delete("/api/v1/chat/sessions/999")
            
            assert response.status_code == 404
            assert "Session not found" in response.json()["detail"]


class TestChatMessageEndpoints:
    """Test chat message endpoints"""
    
    @pytest.mark.asyncio
    async def test_send_message(self, mock_chat_manager, mock_db_session, mock_current_user):
        """Test sending a message"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat/sessions/123/messages",
                json={
                    "content": "What is AI?",
                    "document_id": 456,
                    "similarity_threshold": 0.8
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == 123
            assert data["answer"] == "Test answer"
            assert len(data["sources"]) == 1
            assert data["confidence"] == 0.9
            
            mock_chat_manager.send_message.assert_called_once_with(
                db=mock_db_session,
                session_id=123,
                question="What is AI?",
                document_id=456,
                similarity_threshold=0.8
            )
    
    @pytest.mark.asyncio
    async def test_send_message_minimal(self, mock_chat_manager, mock_db_session, mock_current_user):
        """Test sending message with minimal parameters"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat/sessions/123/messages",
                json={"content": "Hello"}
            )
            
            assert response.status_code == 200
            mock_chat_manager.send_message.assert_called_once_with(
                db=mock_db_session,
                session_id=123,
                question="Hello",
                document_id=None,
                similarity_threshold=0.7  # Default value
            )
    
    @pytest.mark.asyncio
    async def test_send_message_validation_error(self, mock_chat_manager, mock_db_session, mock_current_user):
        """Test message validation error"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat/sessions/123/messages",
                json={"content": ""}  # Empty content
            )
            
            assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_send_message_rag_error(self, mock_chat_manager, mock_db_session, mock_current_user):
        """Test message sending with RAG error"""
        mock_chat_manager.send_message.side_effect = RAGError("Processing failed")
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat/sessions/123/messages",
                json={"content": "Test message"}
            )
            
            assert response.status_code == 500
            assert "Processing failed" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_send_message_stream(self, mock_chat_manager, mock_db_session, mock_current_user):
        """Test streaming message response"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat/sessions/123/messages/stream",
                json={"content": "What is AI?"}
            )
            
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream"
            
            # Check that streaming was called
            mock_chat_manager.stream_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_messages(self, mock_chat_manager, mock_db_session, mock_current_user):
        """Test getting messages from a session"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/chat/sessions/123/messages")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["id"] == 456
            assert data[0]["content"] == "Test message"
            
            mock_chat_manager.get_session.assert_called_once_with(mock_db_session, 123)
            mock_chat_manager.get_session_messages.assert_called_once_with(mock_db_session, 123, 50)
    
    @pytest.mark.asyncio
    async def test_get_messages_with_limit(self, mock_chat_manager, mock_db_session, mock_current_user):
        """Test getting messages with custom limit"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/chat/sessions/123/messages?limit=10")
            
            assert response.status_code == 200
            mock_chat_manager.get_session_messages.assert_called_once_with(mock_db_session, 123, 10)
    
    @pytest.mark.asyncio
    async def test_get_messages_session_not_found(self, mock_chat_manager, mock_db_session, mock_current_user):
        """Test getting messages from non-existent session"""
        mock_chat_manager.get_session.return_value = None
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/chat/sessions/999/messages")
            
            assert response.status_code == 404
            assert "Session not found" in response.json()["detail"]


class TestDirectQueryEndpoints:
    """Test direct query endpoints (without session)"""
    
    @pytest.mark.asyncio
    async def test_direct_query(self, mock_rag_service, mock_current_user):
        """Test direct RAG query"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat/query",
                json={
                    "question": "What is AI?",
                    "document_id": 456,
                    "similarity_threshold": 0.8
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["answer"] == "Direct query answer"
            assert len(data["sources"]) == 1
            assert data["confidence"] == 0.9
            assert data["retrieved_documents"] == 1
            
            mock_rag_service.query.assert_called_once_with(
                question="What is AI?",
                document_id=456,
                similarity_threshold=0.8
            )
    
    @pytest.mark.asyncio
    async def test_direct_query_minimal(self, mock_rag_service, mock_current_user):
        """Test direct query with minimal parameters"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat/query",
                json={"question": "Hello"}
            )
            
            assert response.status_code == 200
            mock_rag_service.query.assert_called_once_with(
                question="Hello",
                document_id=None,
                similarity_threshold=0.7
            )
    
    @pytest.mark.asyncio
    async def test_direct_query_stream(self, mock_rag_service, mock_current_user):
        """Test direct streaming query"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat/query/stream",
                json={"question": "What is AI?"}
            )
            
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream"
            
            mock_rag_service.stream_query.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_direct_query_error(self, mock_rag_service, mock_current_user):
        """Test direct query with RAG error"""
        mock_rag_service.query.side_effect = RAGError("Query failed")
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat/query",
                json={"question": "Test"}
            )
            
            assert response.status_code == 500
            assert "Query failed" in response.json()["detail"]


class TestUtilityEndpoints:
    """Test utility endpoints"""
    
    @pytest.mark.asyncio
    async def test_get_query_suggestions(self, mock_rag_service, mock_current_user):
        """Test getting query suggestions"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/chat/suggestions")
            
            assert response.status_code == 200
            data = response.json()
            assert "suggestions" in data
            assert len(data["suggestions"]) == 3
            assert "What is the main topic?" in data["suggestions"]
            
            mock_rag_service.get_query_suggestions.assert_called_once_with(
                document_id=None,
                limit=5
            )
    
    @pytest.mark.asyncio
    async def test_get_query_suggestions_with_params(self, mock_rag_service, mock_current_user):
        """Test getting suggestions with parameters"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/chat/suggestions?document_id=456&limit=3")
            
            assert response.status_code == 200
            mock_rag_service.get_query_suggestions.assert_called_once_with(
                document_id=456,
                limit=3
            )
    
    @pytest.mark.asyncio
    async def test_analyze_query(self, mock_rag_service, mock_current_user):
        """Test query analysis"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat/analyze",
                json={"question": "What is AI?"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "analysis" in data
            assert data["analysis"]["complexity"] == "simple"
            assert data["analysis"]["word_count"] == 3
            
            mock_rag_service.analyze_query_complexity.assert_called_once_with("What is AI?")
    
    @pytest.mark.asyncio
    async def test_analyze_query_error(self, mock_rag_service, mock_current_user):
        """Test query analysis error"""
        mock_rag_service.analyze_query_complexity.side_effect = Exception("Analysis failed")
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat/analyze",
                json={"question": "Test"}
            )
            
            assert response.status_code == 500
            assert "Failed to analyze query" in response.json()["detail"]


@pytest.mark.asyncio
async def test_authentication_required():
    """Test that endpoints require authentication"""
    # This test would need proper authentication setup
    # For now, we're mocking the current user dependency
    pass


@pytest.mark.asyncio
async def test_request_validation():
    """Test request validation for various endpoints"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test invalid similarity threshold
        response = await client.post(
            "/api/v1/chat/query",
            json={
                "question": "Test",
                "similarity_threshold": 1.5  # Invalid: > 1.0
            }
        )
        assert response.status_code == 422
        
        # Test empty question
        response = await client.post(
            "/api/v1/chat/query",
            json={"question": ""}
        )
        assert response.status_code == 422
        
        # Test question too long
        long_question = "x" * 6000  # Exceeds max_length=5000
        response = await client.post(
            "/api/v1/chat/query",
            json={"question": long_question}
        )
        assert response.status_code == 422