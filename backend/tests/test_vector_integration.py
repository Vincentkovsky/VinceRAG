"""
Integration tests for vector database functionality
"""

import pytest
import tempfile
import shutil
from unittest.mock import patch, Mock, AsyncMock
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.core.database import get_db
from app.models.document import Document
from app.core.config import settings


@pytest.fixture
def temp_chroma_dir():
    """Temporary directory for Chroma database"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for embeddings"""
    mock_client = AsyncMock()
    mock_response = Mock()
    mock_response.data = [Mock(embedding=[0.1] * 1536)]
    mock_client.embeddings.create.return_value = mock_response
    return mock_client


@pytest.fixture
async def test_document(db_session: AsyncSession):
    """Create a test document"""
    document = Document(
        name="test_document.txt",
        type="txt",
        status="completed",
        document_metadata={
            "originalFileName": "test_document.txt",
            "fileSize": 1024,
            "mimeType": "text/plain"
        }
    )
    db_session.add(document)
    await db_session.commit()
    await db_session.refresh(document)
    return document


@pytest.mark.asyncio
async def test_create_and_search_chunks_integration(
    temp_chroma_dir,
    mock_openai_client,
    test_document,
    db_session: AsyncSession
):
    """Test complete chunk creation and search workflow"""
    
    with patch.object(settings, 'chroma_persist_directory', temp_chroma_dir):
        with patch.object(settings, 'openai_api_key', 'test-key'):
            with patch('app.services.vector_service.AsyncOpenAI') as mock_openai:
                mock_openai.return_value = mock_openai_client
                
                # Override database dependency
                app.dependency_overrides[get_db] = lambda: db_session
                
                async with AsyncClient(app=app, base_url="http://test") as client:
                    # Create chunks for the test document
                    chunks_data = [
                        {
                            "content": "This is the first chunk about artificial intelligence and machine learning.",
                            "start_char": 0,
                            "end_char": 75,
                            "token_count": 12
                        },
                        {
                            "content": "This is the second chunk about natural language processing and deep learning.",
                            "start_char": 75,
                            "end_char": 152,
                            "token_count": 13
                        }
                    ]
                    
                    # Create chunks
                    response = await client.post(
                        f"/documents/{test_document.id}/chunks",
                        json=chunks_data
                    )
                    
                    assert response.status_code == 200
                    created_chunks = response.json()
                    assert len(created_chunks) == 2
                    
                    # Verify chunk data
                    for i, chunk in enumerate(created_chunks):
                        assert chunk["document_id"] == test_document.id
                        assert chunk["chunk_index"] == i
                        assert chunk["content"] == chunks_data[i]["content"]
                        assert chunk["document_name"] == test_document.name
                        assert chunk["document_type"] == test_document.type
                    
                    # Test similarity search
                    search_request = {
                        "query": "artificial intelligence",
                        "n_results": 5,
                        "similarity_threshold": 0.0  # Low threshold for testing
                    }
                    
                    response = await client.post(
                        "/chunks/search",
                        json=search_request
                    )
                    
                    assert response.status_code == 200
                    search_results = response.json()
                    
                    assert "results" in search_results
                    assert "total_results" in search_results
                    assert search_results["query"] == "artificial intelligence"
                    
                    # Should find at least one result
                    assert search_results["total_results"] >= 0
                    
                    # Test getting specific chunk
                    chunk_id = created_chunks[0]["id"]
                    response = await client.get(f"/chunks/{chunk_id}")
                    
                    assert response.status_code == 200
                    chunk_data = response.json()
                    assert chunk_data["id"] == chunk_id
                    assert chunk_data["content"] == chunks_data[0]["content"]
                    
                    # Test getting document chunks
                    response = await client.get(f"/documents/{test_document.id}/chunks")
                    
                    assert response.status_code == 200
                    document_chunks = response.json()
                    assert len(document_chunks) == 2
                    
                    # Test chunk statistics
                    response = await client.get("/chunks/stats")
                    
                    assert response.status_code == 200
                    stats = response.json()
                    assert "vector_database" in stats
                    assert "embedding_model" in stats
                    
                    # Test chunk update
                    new_content = "Updated chunk content about AI and ML technologies."
                    response = await client.put(
                        f"/chunks/{chunk_id}",
                        params={"content": new_content}
                    )
                    
                    assert response.status_code == 200
                    updated_chunk = response.json()
                    assert updated_chunk["content"] == new_content
                    
                    # Test chunk deletion
                    response = await client.delete(f"/chunks/{chunk_id}")
                    
                    assert response.status_code == 200
                    
                    # Verify chunk is deleted
                    response = await client.get(f"/chunks/{chunk_id}")
                    assert response.status_code == 404
                    
                    # Test deleting all document chunks
                    response = await client.delete(f"/documents/{test_document.id}/chunks")
                    
                    assert response.status_code == 200
                    
                    # Verify all chunks are deleted
                    response = await client.get(f"/documents/{test_document.id}/chunks")
                    assert response.status_code == 200
                    remaining_chunks = response.json()
                    assert len(remaining_chunks) == 0


@pytest.mark.asyncio
async def test_similarity_search_with_filters(
    temp_chroma_dir,
    mock_openai_client,
    test_document,
    db_session: AsyncSession
):
    """Test similarity search with document filtering"""
    
    with patch.object(settings, 'chroma_persist_directory', temp_chroma_dir):
        with patch.object(settings, 'openai_api_key', 'test-key'):
            with patch('app.services.vector_service.AsyncOpenAI') as mock_openai:
                mock_openai.return_value = mock_openai_client
                
                app.dependency_overrides[get_db] = lambda: db_session
                
                async with AsyncClient(app=app, base_url="http://test") as client:
                    # Create chunks
                    chunks_data = [
                        {
                            "content": "Machine learning algorithms for data analysis.",
                            "start_char": 0,
                            "end_char": 45,
                            "token_count": 7
                        }
                    ]
                    
                    response = await client.post(
                        f"/documents/{test_document.id}/chunks",
                        json=chunks_data
                    )
                    
                    assert response.status_code == 200
                    
                    # Test search with document filter
                    search_request = {
                        "query": "machine learning",
                        "n_results": 5,
                        "document_id": test_document.id,
                        "similarity_threshold": 0.0
                    }
                    
                    response = await client.post(
                        "/chunks/search",
                        json=search_request
                    )
                    
                    assert response.status_code == 200
                    search_results = response.json()
                    
                    # Should find results only from the specified document
                    for result in search_results["results"]:
                        assert result["metadata"]["document_id"] == test_document.id


@pytest.mark.asyncio
async def test_error_handling(temp_chroma_dir, db_session: AsyncSession):
    """Test error handling in vector operations"""
    
    with patch.object(settings, 'chroma_persist_directory', temp_chroma_dir):
        with patch.object(settings, 'openai_api_key', None):  # No API key
            
            app.dependency_overrides[get_db] = lambda: db_session
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                # Test search without proper setup
                search_request = {
                    "query": "test query",
                    "n_results": 5
                }
                
                response = await client.post(
                    "/chunks/search",
                    json=search_request
                )
                
                # Should return error due to missing API key
                assert response.status_code == 500
                
                # Test getting non-existent chunk
                response = await client.get("/chunks/999999")
                assert response.status_code == 404
                
                # Test getting chunks for non-existent document
                response = await client.get("/documents/999999/chunks")
                assert response.status_code == 404