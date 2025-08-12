"""
Tests for advanced RAG features
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from app.services.rag_service import (
    RAGQueryService,
    QueryCache,
    RAGError
)
from app.core.config import settings


class TestQueryCache:
    """Test query cache functionality"""
    
    def test_cache_initialization(self):
        """Test cache initialization"""
        cache = QueryCache(max_size=50, ttl_minutes=15)
        
        assert cache.max_size == 50
        assert cache.ttl == timedelta(minutes=15)
        assert len(cache.cache) == 0
    
    def test_cache_key_generation(self):
        """Test cache key generation"""
        cache = QueryCache()
        
        key1 = cache._generate_key("test query", None, 0.7)
        key2 = cache._generate_key("test query", None, 0.7)
        key3 = cache._generate_key("different query", None, 0.7)
        key4 = cache._generate_key("test query", 123, 0.7)
        
        assert key1 == key2  # Same parameters should generate same key
        assert key1 != key3  # Different query should generate different key
        assert key1 != key4  # Different document_id should generate different key
    
    def test_cache_set_and_get(self):
        """Test setting and getting cache values"""
        cache = QueryCache()
        
        result = {"answer": "test answer", "confidence": 0.9}
        cache.set("test query", None, 0.7, result)
        
        retrieved = cache.get("test query", None, 0.7)
        assert retrieved == result
    
    def test_cache_miss(self):
        """Test cache miss"""
        cache = QueryCache()
        
        retrieved = cache.get("nonexistent query", None, 0.7)
        assert retrieved is None
    
    def test_cache_expiration(self):
        """Test cache expiration"""
        cache = QueryCache(ttl_minutes=0)  # Immediate expiration
        
        result = {"answer": "test answer"}
        cache.set("test query", None, 0.7, result)
        
        # Should be expired immediately
        retrieved = cache.get("test query", None, 0.7)
        assert retrieved is None
    
    def test_cache_size_limit(self):
        """Test cache size limit"""
        cache = QueryCache(max_size=2)
        
        cache.set("query1", None, 0.7, {"answer": "answer1"})
        cache.set("query2", None, 0.7, {"answer": "answer2"})
        cache.set("query3", None, 0.7, {"answer": "answer3"})
        
        # Should only have 2 items (oldest should be evicted)
        assert len(cache.cache) == 2
        assert cache.get("query1", None, 0.7) is None  # Should be evicted
        assert cache.get("query2", None, 0.7) is not None
        assert cache.get("query3", None, 0.7) is not None
    
    def test_cache_clear(self):
        """Test cache clearing"""
        cache = QueryCache()
        
        cache.set("query1", None, 0.7, {"answer": "answer1"})
        cache.set("query2", None, 0.7, {"answer": "answer2"})
        
        assert len(cache.cache) == 2
        
        cache.clear()
        assert len(cache.cache) == 0


class TestAdvancedRAGFeatures:
    """Test advanced RAG features"""
    
    @pytest.fixture
    def mock_langchain_components(self):
        """Mock LangChain components"""
        with patch('app.services.rag_service.ChatOpenAI') as mock_llm:
            mock_llm_instance = AsyncMock()
            mock_llm_instance.ainvoke.return_value = Mock(content="Test response")
            mock_llm.return_value = mock_llm_instance
            yield {'llm': mock_llm, 'llm_instance': mock_llm_instance}
    
    @pytest.fixture
    def mock_vector_service(self):
        """Mock vector service"""
        with patch('app.services.rag_service.chunk_storage_manager') as mock_manager:
            mock_manager.similarity_search = AsyncMock(return_value=[
                {
                    "content": "Test document content",
                    "similarity": 0.9,
                    "metadata": {"chunk_id": 123, "document_id": 456, "chunk_index": 0},
                    "chunk_id": 123,
                    "document_id": 456,
                    "chunk_index": 0
                }
            ])
            yield mock_manager
    
    @pytest.mark.asyncio
    async def test_query_optimization(self, mock_langchain_components, mock_vector_service):
        """Test query optimization"""
        with patch.object(settings, 'openai_api_key', 'test-key'):
            service = RAGQueryService()
            
            # Test with short query and chat history
            chat_history = [
                {"role": "user", "content": "What is machine learning and artificial intelligence?"},
                {"role": "assistant", "content": "ML is a subset of AI that focuses on algorithms."}
            ]
            
            # Use a very short query that should trigger expansion
            short_query = "More"
            optimized = await service.optimize_query(short_query, chat_history)
            
            # Should include context from chat history for very short queries
            assert short_query in optimized
            # For short queries (<=2 words), context should be added
            if len(short_query.split()) <= 2:
                assert len(optimized) > len(short_query)
            
            # Test without chat history
            optimized_no_history = await service.optimize_query("What is AI?", None)
            assert optimized_no_history == "What is AI?"
    
    @pytest.mark.asyncio
    async def test_result_ranking(self, mock_langchain_components, mock_vector_service):
        """Test result ranking"""
        with patch.object(settings, 'openai_api_key', 'test-key'):
            service = RAGQueryService()
            
            results = [
                {
                    "content": "Document 1",
                    "similarity": 0.8,
                    "metadata": {"title": "AI Overview", "document_type": "pdf"}
                },
                {
                    "content": "Document 2", 
                    "similarity": 0.9,
                    "metadata": {"title": "Machine Learning", "document_type": "txt"}
                }
            ]
            
            ranked = await service.rank_results(results, "AI overview")  # Use "AI" to match title
            
            # Should have enhanced scores
            assert all("enhanced_score" in result for result in ranked)
            # Should boost results with query terms in title
            ai_doc = next(r for r in ranked if "AI" in r["metadata"]["title"])
            # The boost should be applied (1.15x for title match)
            assert ai_doc["enhanced_score"] > ai_doc["similarity"]
            # Check that the boost was applied correctly
            expected_score = ai_doc["similarity"] * 1.15
            assert abs(ai_doc["enhanced_score"] - expected_score) < 0.01
    
    @pytest.mark.asyncio
    async def test_no_results_handling(self, mock_langchain_components):
        """Test handling of no results"""
        with patch.object(settings, 'openai_api_key', 'test-key'):
            service = RAGQueryService()
            
            response = await service.handle_no_results("complex technical query")
            
            assert "message" in response
            assert "suggestions" in response
            assert "alternative_queries" in response
            assert "tips" in response
            # Suggestions might be empty if analysis fails, but structure should be there
            assert isinstance(response["suggestions"], list)
    
    @pytest.mark.asyncio
    async def test_query_with_caching(self, mock_langchain_components, mock_vector_service):
        """Test query with caching enabled"""
        with patch.object(settings, 'openai_api_key', 'test-key'):
            service = RAGQueryService()
            
            # First query - should not be cached
            result1 = await service.query("What is AI?", use_cache=True)
            assert result1["from_cache"] is False
            
            # Second identical query - should be cached
            result2 = await service.query("What is AI?", use_cache=True)
            assert result2["from_cache"] is True
            assert result2["answer"] == result1["answer"]
    
    @pytest.mark.asyncio
    async def test_query_without_caching(self, mock_langchain_components, mock_vector_service):
        """Test query without caching"""
        with patch.object(settings, 'openai_api_key', 'test-key'):
            service = RAGQueryService()
            
            result1 = await service.query("What is AI?", use_cache=False)
            result2 = await service.query("What is AI?", use_cache=False)
            
            assert result1["from_cache"] is False
            assert result2["from_cache"] is False
    
    @pytest.mark.asyncio
    async def test_query_with_no_results(self, mock_langchain_components):
        """Test query when no documents are found"""
        with patch('app.services.rag_service.chunk_storage_manager') as mock_manager:
            mock_manager.similarity_search = AsyncMock(return_value=[])
            
            with patch.object(settings, 'openai_api_key', 'test-key'):
                service = RAGQueryService()
                
                result = await service.query("nonexistent topic")
                
                assert result["retrieved_documents"] == 0
                assert result["confidence"] == 0.0
                assert "suggestions" in result
                assert "alternative_queries" in result
    
    @pytest.mark.asyncio
    async def test_performance_warning(self, mock_langchain_components, mock_vector_service):
        """Test performance warning for slow queries"""
        with patch.object(settings, 'openai_api_key', 'test-key'):
            service = RAGQueryService()
            
            # Mock slow LLM response
            async def slow_ainvoke(messages):
                import asyncio
                await asyncio.sleep(0.1)  # Simulate slow response
                return Mock(content="Slow response")
            
            service.llm_non_streaming.ainvoke = slow_ainvoke
            
            # Mock datetime to simulate long processing time
            with patch('app.services.rag_service.datetime') as mock_datetime:
                start_time = datetime.now()
                end_time = start_time + timedelta(seconds=6)  # 6 seconds
                mock_datetime.now.side_effect = [start_time, end_time, end_time]  # Add extra call for cache
                
                result = await service.query("test query", use_cache=False)  # Disable cache to avoid issues
                
                assert "performance_warning" in result
    
    @pytest.mark.asyncio
    async def test_cache_stats(self, mock_langchain_components):
        """Test cache statistics"""
        with patch.object(settings, 'openai_api_key', 'test-key'):
            service = RAGQueryService()
            
            stats = service.get_cache_stats()
            
            assert "cache_size" in stats
            assert "max_cache_size" in stats
            assert "ttl_minutes" in stats
            assert "cache_keys" in stats
            assert stats["cache_size"] == 0  # Empty initially
    
    @pytest.mark.asyncio
    async def test_cache_clear(self, mock_langchain_components, mock_vector_service):
        """Test cache clearing"""
        with patch.object(settings, 'openai_api_key', 'test-key'):
            service = RAGQueryService()
            
            # Add something to cache
            await service.query("test query", use_cache=True)
            
            stats_before = service.get_cache_stats()
            assert stats_before["cache_size"] > 0
            
            service.clear_cache()
            
            stats_after = service.get_cache_stats()
            assert stats_after["cache_size"] == 0
    
    @pytest.mark.asyncio
    async def test_query_with_all_features_enabled(self, mock_langchain_components, mock_vector_service):
        """Test query with all advanced features enabled"""
        with patch.object(settings, 'openai_api_key', 'test-key'):
            service = RAGQueryService()
            
            result = await service.query(
                "What is artificial intelligence?",
                document_id=123,
                chat_history=[{"role": "user", "content": "Hello"}],
                similarity_threshold=0.8,
                enable_query_optimization=True,
                enable_result_ranking=True,
                use_cache=False  # Disabled due to chat history
            )
            
            assert "answer" in result
            assert "sources" in result
            assert "confidence" in result
            assert "processing_time" in result
            assert "retrieved_documents" in result
            assert "query_optimized" in result
            assert result["from_cache"] is False
    
    @pytest.mark.asyncio
    async def test_query_with_features_disabled(self, mock_langchain_components, mock_vector_service):
        """Test query with advanced features disabled"""
        with patch.object(settings, 'openai_api_key', 'test-key'):
            service = RAGQueryService()
            
            result = await service.query(
                "What is AI?",
                enable_query_optimization=False,
                enable_result_ranking=False,
                use_cache=False
            )
            
            assert "answer" in result
            assert result["query_optimized"] is False
            assert result["from_cache"] is False
            # Enhanced scores should not be present when ranking is disabled
            for source in result["sources"]:
                assert "enhanced_score" not in source or source["enhanced_score"] == source["similarity"]


@pytest.mark.asyncio
async def test_integration_advanced_features():
    """Integration test for advanced RAG features"""
    with patch.object(settings, 'openai_api_key', 'test-key'):
        with patch('app.services.rag_service.ChatOpenAI') as mock_llm, \
             patch('app.services.rag_service.chunk_storage_manager') as mock_manager:
            
            # Setup mocks
            mock_llm_instance = AsyncMock()
            mock_llm_instance.ainvoke.return_value = Mock(content="Advanced AI response")
            mock_llm.return_value = mock_llm_instance
            
            mock_manager.similarity_search = AsyncMock(return_value=[
                {
                    "content": "AI is artificial intelligence",
                    "similarity": 0.95,
                    "metadata": {"chunk_id": 1, "document_id": 1, "chunk_index": 0, "title": "AI Guide"},
                    "chunk_id": 1,
                    "document_id": 1,
                    "chunk_index": 0
                }
            ])
            
            # Test complete flow
            service = RAGQueryService()
            
            # Test with all features
            result = await service.query(
                "What is artificial intelligence?",
                enable_query_optimization=True,
                enable_result_ranking=True,
                use_cache=True
            )
            
            assert result["answer"] == "Advanced AI response"
            assert len(result["sources"]) == 1
            assert result["confidence"] > 0.9
            assert result["from_cache"] is False
            
            # Test caching
            cached_result = await service.query(
                "What is artificial intelligence?",
                use_cache=True
            )
            assert cached_result["from_cache"] is True