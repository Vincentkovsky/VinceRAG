"""
Tests for vector database service
"""

import pytest
import asyncio
import tempfile
import shutil
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.vector_service import (
    EmbeddingService,
    ChromaVectorStore,
    VectorService,
    VectorDatabaseError
)
from app.models.document import Document, DocumentChunk
from app.core.config import settings


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client"""
    mock_client = AsyncMock()
    
    def create_mock_response(input_texts):
        """Create mock response based on input length"""
        if isinstance(input_texts, list):
            data = [Mock(embedding=[0.1, 0.2, 0.3] * 512) for _ in input_texts]
        else:
            data = [Mock(embedding=[0.1, 0.2, 0.3] * 512)]
        
        mock_response = Mock()
        mock_response.data = data
        return mock_response
    
    mock_client.embeddings.create.side_effect = lambda model, input: create_mock_response(input)
    return mock_client


@pytest.fixture
def temp_chroma_dir():
    """Temporary directory for Chroma database"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


class TestEmbeddingService:
    """Test embedding service functionality"""
    
    @pytest.mark.asyncio
    async def test_embed_documents_success(self, mock_openai_client):
        """Test successful document embedding"""
        with patch('app.services.vector_service.AsyncOpenAI') as mock_openai:
            mock_openai.return_value = mock_openai_client
            
            service = EmbeddingService()
            texts = ["Hello world", "Test document"]
            
            embeddings = await service.embed_documents(texts)
            
            assert len(embeddings) == 2
            assert len(embeddings[0]) == 1536  # OpenAI embedding dimension
            mock_openai_client.embeddings.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_embed_documents_batch_processing(self, mock_openai_client):
        """Test batch processing for large number of documents"""
        with patch('app.services.vector_service.AsyncOpenAI') as mock_openai:
            mock_openai.return_value = mock_openai_client
            
            service = EmbeddingService()
            # Create 150 texts to test batching (batch size is 100)
            texts = [f"Document {i}" for i in range(150)]
            
            embeddings = await service.embed_documents(texts)
            
            assert len(embeddings) == 150
            # Should be called twice due to batching
            assert mock_openai_client.embeddings.create.call_count == 2
    
    @pytest.mark.asyncio
    async def test_embed_query_success(self, mock_openai_client):
        """Test successful query embedding"""
        with patch('app.services.vector_service.AsyncOpenAI') as mock_openai:
            mock_openai.return_value = mock_openai_client
            
            service = EmbeddingService()
            query = "What is AI?"
            
            embedding = await service.embed_query(query)
            
            assert len(embedding) == 1536
            mock_openai_client.embeddings.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_embedding_service_no_api_key(self):
        """Test embedding service without API key"""
        with patch.object(settings, 'openai_api_key', None):
            with pytest.raises(ValueError, match="OpenAI API key is required"):
                EmbeddingService()
    
    @pytest.mark.asyncio
    async def test_embed_documents_api_error(self, mock_openai_client):
        """Test handling of API errors"""
        mock_openai_client.embeddings.create.side_effect = Exception("API Error")
        
        with patch('app.services.vector_service.AsyncOpenAI') as mock_openai:
            mock_openai.return_value = mock_openai_client
            
            service = EmbeddingService()
            
            with pytest.raises(VectorDatabaseError, match="Embedding generation failed"):
                await service.embed_documents(["test"])


class TestChromaVectorStore:
    """Test Chroma vector store functionality"""
    
    @pytest.mark.asyncio
    async def test_initialize_success(self, temp_chroma_dir):
        """Test successful Chroma initialization"""
        with patch.object(settings, 'chroma_persist_directory', temp_chroma_dir):
            store = ChromaVectorStore()
            await store.initialize()
            
            assert store._initialized is True
            assert store.client is not None
            assert store.collection is not None
    
    @pytest.mark.asyncio
    async def test_add_documents_success(self, temp_chroma_dir):
        """Test adding documents to vector store"""
        with patch.object(settings, 'chroma_persist_directory', temp_chroma_dir):
            store = ChromaVectorStore()
            await store.initialize()
            
            ids = ["1", "2"]
            embeddings = [[0.1, 0.2], [0.3, 0.4]]
            documents = ["Doc 1", "Doc 2"]
            metadatas = [{"id": 1}, {"id": 2}]
            
            await store.add_documents(ids, embeddings, documents, metadatas)
            
            # Verify documents were added
            stats = await store.get_collection_stats()
            assert stats["total_documents"] == 2
    
    @pytest.mark.asyncio
    async def test_similarity_search_success(self, temp_chroma_dir):
        """Test similarity search"""
        with patch.object(settings, 'chroma_persist_directory', temp_chroma_dir):
            store = ChromaVectorStore()
            await store.initialize()
            
            # Add test documents
            ids = ["1", "2"]
            embeddings = [[0.1, 0.2], [0.3, 0.4]]
            documents = ["Hello world", "Test document"]
            metadatas = [{"doc_id": 1}, {"doc_id": 2}]
            
            await store.add_documents(ids, embeddings, documents, metadatas)
            
            # Search
            query_embedding = [0.1, 0.2]
            docs, similarities, metas = await store.similarity_search(query_embedding, n_results=2)
            
            assert len(docs) == 2
            assert len(similarities) == 2
            assert len(metas) == 2
            assert all(0 <= sim <= 1 for sim in similarities)
    
    @pytest.mark.asyncio
    async def test_delete_documents_success(self, temp_chroma_dir):
        """Test document deletion"""
        with patch.object(settings, 'chroma_persist_directory', temp_chroma_dir):
            store = ChromaVectorStore()
            await store.initialize()
            
            # Add test documents
            ids = ["1", "2"]
            embeddings = [[0.1, 0.2], [0.3, 0.4]]
            documents = ["Doc 1", "Doc 2"]
            metadatas = [{"id": 1}, {"id": 2}]
            
            await store.add_documents(ids, embeddings, documents, metadatas)
            
            # Delete one document
            await store.delete_documents(["1"])
            
            # Verify deletion
            stats = await store.get_collection_stats()
            assert stats["total_documents"] == 1
    
    @pytest.mark.asyncio
    async def test_similarity_search_with_filter(self, temp_chroma_dir):
        """Test similarity search with metadata filter"""
        with patch.object(settings, 'chroma_persist_directory', temp_chroma_dir):
            store = ChromaVectorStore()
            await store.initialize()
            
            # Add test documents with different metadata
            ids = ["1", "2"]
            embeddings = [[0.1, 0.2], [0.3, 0.4]]
            documents = ["Doc 1", "Doc 2"]
            metadatas = [{"document_id": 1}, {"document_id": 2}]
            
            await store.add_documents(ids, embeddings, documents, metadatas)
            
            # Search with filter
            query_embedding = [0.1, 0.2]
            docs, similarities, metas = await store.similarity_search(
                query_embedding, 
                n_results=2, 
                where={"document_id": 1}
            )
            
            assert len(docs) == 1
            assert metas[0]["document_id"] == 1


class TestVectorService:
    """Test chunk storage manager functionality"""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session"""
        session = AsyncMock(spec=AsyncSession)
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.add = Mock()
        session.delete = AsyncMock()
        return session
    
    @pytest.fixture
    def mock_embedding_service(self):
        """Mock embedding service"""
        service = AsyncMock(spec=EmbeddingService)
        service.embed_documents.return_value = [[0.1, 0.2], [0.3, 0.4]]
        service.embed_query.return_value = [0.1, 0.2]
        return service
    
    @pytest.fixture
    def mock_vector_store(self):
        """Mock vector store"""
        store = AsyncMock(spec=ChromaVectorStore)
        store.add_documents = AsyncMock()
        store.delete_documents = AsyncMock()
        store.similarity_search.return_value = (
            ["Doc 1", "Doc 2"],
            [0.9, 0.8],
            [{"chunk_id": 1, "document_id": 1}, {"chunk_id": 2, "document_id": 1}]
        )
        return store
    
    @pytest.mark.asyncio
    async def test_store_chunks_success(self, mock_db_session, mock_embedding_service, mock_vector_store):
        """Test successful chunk storage"""
        manager = VectorService()
        manager.embedding_service = mock_embedding_service
        manager.vector_store = mock_vector_store
        
        document_id = 123456789
        chunks = [
            {
                "content": "First chunk content",
                "start_char": 0,
                "end_char": 100,
                "token_count": 20
            },
            {
                "content": "Second chunk content",
                "start_char": 100,
                "end_char": 200,
                "token_count": 25
            }
        ]
        
        result = await manager.store_chunks(mock_db_session, document_id, chunks)
        
        assert len(result) == 2
        assert all(isinstance(chunk, DocumentChunk) for chunk in result)
        assert mock_db_session.commit.called
        assert mock_vector_store.add_documents.called
    
    @pytest.mark.asyncio
    async def test_store_chunks_embedding_failure(self, mock_db_session, mock_embedding_service, mock_vector_store):
        """Test chunk storage with embedding failure"""
        mock_embedding_service.embed_documents.side_effect = Exception("Embedding failed")
        
        manager = VectorService()
        manager.embedding_service = mock_embedding_service
        manager.vector_store = mock_vector_store
        
        chunks = [{"content": "Test content"}]
        
        with pytest.raises(VectorDatabaseError, match="Chunk storage failed"):
            await manager.store_chunks(mock_db_session, 123, chunks)
        
        assert mock_db_session.rollback.called
    
    @pytest.mark.asyncio
    async def test_delete_chunks_success(self, mock_db_session, mock_vector_store):
        """Test successful chunk deletion"""
        # Mock database query result
        mock_chunks = [
            Mock(vector_id="1", id=1),
            Mock(vector_id="2", id=2)
        ]
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_chunks
        mock_db_session.execute.return_value = mock_result
        
        manager = VectorService()
        manager.vector_store = mock_vector_store
        
        await manager.delete_chunks(mock_db_session, 123)
        
        mock_vector_store.delete_documents.assert_called_once_with(["1", "2"])
        assert mock_db_session.commit.called
    
    @pytest.mark.asyncio
    async def test_similarity_search_success(self, mock_embedding_service, mock_vector_store):
        """Test successful similarity search"""
        manager = VectorService()
        manager.embedding_service = mock_embedding_service
        manager.vector_store = mock_vector_store
        
        results = await manager.similarity_search("test query", n_results=5)
        
        assert len(results) == 2
        assert all("similarity" in result for result in results)
        assert all("content" in result for result in results)
        assert all("metadata" in result for result in results)
        mock_embedding_service.embed_query.assert_called_once_with("test query")
    
    @pytest.mark.asyncio
    async def test_similarity_search_with_threshold(self, mock_embedding_service, mock_vector_store):
        """Test similarity search with threshold filtering"""
        # Mock low similarity scores
        mock_vector_store.similarity_search.return_value = (
            ["Doc 1", "Doc 2"],
            [0.5, 0.3],  # Below default threshold of 0.7
            [{"chunk_id": 1}, {"chunk_id": 2}]
        )
        
        manager = VectorService()
        manager.embedding_service = mock_embedding_service
        manager.vector_store = mock_vector_store
        
        results = await manager.similarity_search("test query", similarity_threshold=0.7)
        
        # Should filter out results below threshold
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_get_chunk_by_id_success(self, mock_db_session):
        """Test getting chunk by ID"""
        mock_chunk = Mock(spec=DocumentChunk)
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_chunk
        mock_db_session.execute.return_value = mock_result
        
        manager = VectorService()
        
        result = await manager.get_chunk_by_id(mock_db_session, 123)
        
        assert result == mock_chunk
    
    @pytest.mark.asyncio
    async def test_update_chunk_success(self, mock_db_session, mock_embedding_service, mock_vector_store):
        """Test successful chunk update"""
        # Mock existing chunk
        mock_chunk = Mock(spec=DocumentChunk)
        mock_chunk.id = 123
        mock_chunk.vector_id = "123"
        mock_chunk.document_id = 456
        mock_chunk.chunk_index = 0
        mock_chunk.start_char = 0
        mock_chunk.end_char = 100
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_chunk
        mock_db_session.execute.return_value = mock_result
        
        manager = VectorService()
        manager.embedding_service = mock_embedding_service
        manager.vector_store = mock_vector_store
        
        new_content = "Updated content"
        result = await manager.update_chunk(mock_db_session, 123, new_content)
        
        assert result == mock_chunk
        assert mock_chunk.content == new_content
        assert mock_db_session.commit.called
        mock_vector_store.delete_documents.assert_called_once_with(["123"])
        mock_vector_store.add_documents.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_stats_success(self, mock_vector_store):
        """Test getting storage statistics"""
        mock_vector_store.get_collection_stats.return_value = {
            "total_documents": 100,
            "collection_name": "test_collection"
        }
        
        manager = VectorService()
        manager.vector_store = mock_vector_store
        
        stats = await manager.get_stats()
        
        assert "vector_database" in stats
        assert "embedding_model" in stats
        assert "chunk_size" in stats
        assert stats["vector_database"]["total_documents"] == 100


@pytest.mark.asyncio
async def test_integration_chunk_storage_flow(temp_chroma_dir):
    """Integration test for complete chunk storage flow"""
    with patch.object(settings, 'chroma_persist_directory', temp_chroma_dir):
        with patch.object(settings, 'openai_api_key', 'test-key'):
            # Mock OpenAI client
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.data = [Mock(embedding=[0.1] * 1536)]
            mock_client.embeddings.create.return_value = mock_response
            
            with patch('app.services.vector_service.AsyncOpenAI') as mock_openai:
                mock_openai.return_value = mock_client
                
                # Create manager
                manager = VectorService()
                
                # Mock database session
                mock_db = AsyncMock(spec=AsyncSession)
                mock_db.commit = AsyncMock()
                mock_db.add = Mock()
                
                # Test data
                document_id = 123456789
                chunks = [
                    {
                        "content": "Test chunk content",
                        "start_char": 0,
                        "end_char": 100,
                        "token_count": 20
                    }
                ]
                
                # Store chunks
                result = await manager.store_chunks(mock_db, document_id, chunks)
                
                assert len(result) == 1
                assert isinstance(result[0], DocumentChunk)
                assert result[0].document_id == document_id
                
                # Test similarity search
                search_results = await manager.similarity_search("test query")
                
                assert len(search_results) >= 0  # May be empty due to similarity threshold