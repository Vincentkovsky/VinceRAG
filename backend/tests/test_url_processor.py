"""
Tests for URL processor
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock

from app.services.url_processor import URLProcessor, URLProcessingError


class TestURLProcessor:
    """Test cases for URLProcessor"""
    
    @pytest.fixture
    def url_processor(self):
        """Create a URLProcessor instance for testing"""
        return URLProcessor()
    
    @pytest.mark.asyncio
    async def test_create_chunks_basic(self, url_processor):
        """Test basic text chunking"""
        text = "This is a test text. " * 100  # Create text longer than chunk size
        
        chunks = await url_processor._create_chunks(text)
        
        assert len(chunks) > 1  # Should create multiple chunks
        assert all('chunk_index' in chunk for chunk in chunks)
        assert all('content' in chunk for chunk in chunks)
        assert all('start_char' in chunk for chunk in chunks)
        assert all('end_char' in chunk for chunk in chunks)
        assert all('token_count' in chunk for chunk in chunks)
        
        # Check chunk ordering
        for i, chunk in enumerate(chunks):
            assert chunk['chunk_index'] == i
        
        # Check position information
        assert chunks[0]['start_char'] == 0
        for i in range(1, len(chunks)):
            assert chunks[i]['start_char'] >= chunks[i-1]['start_char']
    
    @pytest.mark.asyncio
    async def test_create_chunks_empty_text(self, url_processor):
        """Test chunking with empty text"""
        with pytest.raises(URLProcessingError, match="No text content to chunk"):
            await url_processor._create_chunks("")
        
        with pytest.raises(URLProcessingError, match="No text content to chunk"):
            await url_processor._create_chunks("   ")
    
    @pytest.mark.asyncio
    async def test_create_chunks_short_text(self, url_processor):
        """Test chunking with text shorter than chunk size"""
        text = "This is a short text."
        
        chunks = await url_processor._create_chunks(text)
        
        assert len(chunks) == 1
        assert chunks[0]['content'] == text
        assert chunks[0]['start_char'] == 0
        assert chunks[0]['end_char'] == len(text)
        assert chunks[0]['token_count'] > 0
    
    @pytest.mark.asyncio
    @patch('app.services.url_processor.get_db')
    async def test_create_url_document(self, mock_get_db, url_processor):
        """Test URL document creation"""
        # Mock database session
        mock_db = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db
        
        url = "https://example.com/test-page"
        metadata = {
            'title': 'Test Page',
            'description': 'A test page',
            'domain': 'example.com',
            'scraped_at': '2024-01-15T10:30:00Z',
            'word_count': 100,
            'char_count': 500
        }
        
        # Mock document creation
        mock_document = Mock()
        mock_document.id = 123456789
        mock_db.add = Mock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        with patch('app.services.url_processor.generate_id', return_value=123456789):
            with patch('app.services.url_processor.Document', return_value=mock_document):
                document = await url_processor._create_url_document(mock_db, url, metadata)
                
                assert document == mock_document
                mock_db.add.assert_called_once_with(mock_document)
                mock_db.commit.assert_called_once()
                mock_db.refresh.assert_called_once_with(mock_document)
    
    @pytest.mark.asyncio
    @patch('app.services.url_processor.get_db')
    async def test_store_chunks(self, mock_get_db, url_processor):
        """Test chunk storage in database"""
        # Mock database session
        mock_db = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db
        
        document_id = 123456789
        chunks_data = [
            {
                'chunk_index': 0,
                'content': 'First chunk content',
                'start_char': 0,
                'end_char': 19,
                'token_count': 4
            },
            {
                'chunk_index': 1,
                'content': 'Second chunk content',
                'start_char': 19,
                'end_char': 39,
                'token_count': 4
            }
        ]
        
        # Mock chunk creation
        mock_chunks = [Mock(), Mock()]
        for i, mock_chunk in enumerate(mock_chunks):
            mock_chunk.id = 987654321 + i
        
        mock_db.add = Mock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        with patch('app.services.url_processor.generate_id', side_effect=[987654321, 987654322]):
            with patch('app.services.url_processor.DocumentChunk', side_effect=mock_chunks):
                result = await url_processor._store_chunks(mock_db, document_id, chunks_data)
                
                assert len(result) == 2
                assert result == mock_chunks
                assert mock_db.add.call_count == 2
                mock_db.commit.assert_called_once()
                assert mock_db.refresh.call_count == 2
    
    @pytest.mark.asyncio
    @patch('app.services.url_processor.get_db')
    async def test_store_chunks_error_handling(self, mock_get_db, url_processor):
        """Test chunk storage error handling"""
        # Mock database session that fails
        mock_db = AsyncMock()
        mock_db.add = Mock(side_effect=Exception("Database error"))
        mock_db.rollback = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db
        
        document_id = 123456789
        chunks_data = [{'chunk_index': 0, 'content': 'test', 'start_char': 0, 'end_char': 4, 'token_count': 1}]
        
        with pytest.raises(URLProcessingError, match="Failed to store chunks"):
            await url_processor._store_chunks(mock_db, document_id, chunks_data)
        
        mock_db.rollback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_url_duplicate(self, url_processor):
        """Test URL duplicate checking"""
        url = "https://example.com/test"
        
        # Mock the web scraper validation
        with patch.object(url_processor.web_scraper, '_validate_and_normalize_url', 
                         return_value=url) as mock_validate:
            with patch('app.services.url_processor.get_db') as mock_get_db:
                # Mock database query
                mock_db = AsyncMock()
                mock_result = Mock()
                mock_result.scalar_one_or_none.return_value = None  # No duplicate
                mock_db.execute.return_value = mock_result
                mock_get_db.return_value.__aenter__.return_value = mock_db
                
                result = await url_processor.check_url_duplicate(url)
                
                assert result is None
                mock_validate.assert_called_once_with(url)
                mock_db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_url_duplicate_found(self, url_processor):
        """Test URL duplicate checking when duplicate exists"""
        url = "https://example.com/test"
        existing_doc_id = 123456789
        
        # Mock the web scraper validation
        with patch.object(url_processor.web_scraper, '_validate_and_normalize_url', 
                         return_value=url):
            with patch('app.services.url_processor.get_db') as mock_get_db:
                # Mock database query that finds duplicate
                mock_db = AsyncMock()
                mock_result = Mock()
                mock_result.scalar_one_or_none.return_value = existing_doc_id
                mock_db.execute.return_value = mock_result
                mock_get_db.return_value.__aenter__.return_value = mock_db
                
                result = await url_processor.check_url_duplicate(url)
                
                assert result == existing_doc_id
    
    @pytest.mark.asyncio
    async def test_check_url_duplicate_error_handling(self, url_processor):
        """Test URL duplicate checking error handling"""
        url = "https://example.com/test"
        
        # Mock the web scraper validation to fail
        with patch.object(url_processor.web_scraper, '_validate_and_normalize_url', 
                         side_effect=Exception("Validation error")):
            result = await url_processor.check_url_duplicate(url)
            
            # Should return None on error to allow processing to proceed
            assert result is None


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])