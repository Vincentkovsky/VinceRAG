"""
Tests for document processing pipeline
"""

import pytest
import tempfile
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.document_processor import DocumentProcessor, DocumentProcessingError
from app.models.document import Document, DocumentChunk


class TestDocumentProcessor:
    """Test cases for DocumentProcessor"""
    
    @pytest.fixture
    def processor(self):
        """Create DocumentProcessor instance"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield DocumentProcessor(storage_path=temp_dir)
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def mock_document(self):
        """Create mock document"""
        doc = MagicMock(spec=Document)
        doc.id = 123456789
        doc.name = "test.txt"
        doc.type = "txt"
        doc.status = "processing"
        doc.document_metadata = {}
        return doc
    
    def test_save_uploaded_file(self, processor, temp_dir):
        """Test saving uploaded file"""
        file_content = b"test file content"
        filename = "test.txt"
        document_id = 123456789
        
        file_path = processor.save_uploaded_file(file_content, filename, document_id)
        
        # Check file was saved
        assert Path(file_path).exists()
        assert Path(file_path).read_bytes() == file_content
        assert str(document_id) in file_path
        assert filename in file_path
    
    def test_cleanup_file(self, processor, temp_dir):
        """Test file cleanup"""
        # Create a test file
        test_file = temp_dir / "test.txt"
        test_file.write_text("test content")
        
        assert test_file.exists()
        
        # Cleanup file
        processor.cleanup_file(str(test_file))
        
        assert not test_file.exists()
    
    def test_cleanup_nonexistent_file(self, processor):
        """Test cleanup of non-existent file doesn't raise error"""
        # Should not raise exception
        processor.cleanup_file("nonexistent_file.txt")
    
    @pytest.mark.asyncio
    async def test_extract_text(self, processor, temp_dir):
        """Test text extraction"""
        # Create test file
        test_file = temp_dir / "test.txt"
        content = "This is test content for extraction."
        test_file.write_text(content)
        
        # Mock text extractor
        mock_result = {
            'text': content,
            'file_hash': 'abc123',
            'file_size': len(content),
            'file_type': 'txt',
            'metadata': {'encoding': 'utf-8'}
        }
        
        with patch.object(processor.text_extractor, 'extract_text', return_value=mock_result):
            result = await processor._extract_text(str(test_file), "txt")
            
            assert result == mock_result
    
    @pytest.mark.asyncio
    async def test_create_chunks(self, processor):
        """Test text chunking"""
        text = "This is a long text that should be split into multiple chunks. " * 50
        
        chunks = await processor._create_chunks(text)
        
        assert len(chunks) > 1  # Should create multiple chunks
        assert all('chunk_index' in chunk for chunk in chunks)
        assert all('content' in chunk for chunk in chunks)
        assert all('start_char' in chunk for chunk in chunks)
        assert all('end_char' in chunk for chunk in chunks)
        assert all('token_count' in chunk for chunk in chunks)
        
        # Check chunk indices are sequential
        for i, chunk in enumerate(chunks):
            assert chunk['chunk_index'] == i
    
    @pytest.mark.asyncio
    async def test_create_chunks_empty_text(self, processor):
        """Test chunking with empty text"""
        with pytest.raises(DocumentProcessingError, match="No text content to chunk"):
            await processor._create_chunks("")
    
    @pytest.mark.asyncio
    async def test_store_chunks(self, processor, mock_document):
        """Test storing chunks in database"""
        chunks = [
            {
                'chunk_index': 0,
                'content': 'First chunk content',
                'start_char': 0,
                'end_char': 19,
                'token_count': 5
            },
            {
                'chunk_index': 1,
                'content': 'Second chunk content',
                'start_char': 19,
                'end_char': 39,
                'token_count': 5
            }
        ]
        
        # Mock database session
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        with patch('app.services.document_processor.generate_id', side_effect=[111, 222]):
            chunk_records = await processor._store_chunks(mock_db, 123456789, chunks)
            
            assert len(chunk_records) == 2
            assert mock_db.add.call_count == 2
            assert mock_db.commit.called
            assert mock_db.refresh.call_count == 2
    
    @pytest.mark.asyncio
    async def test_store_chunks_database_error(self, processor):
        """Test chunk storage with database error"""
        chunks = [{'chunk_index': 0, 'content': 'test', 'start_char': 0, 'end_char': 4, 'token_count': 1}]
        
        # Mock database session that raises error on commit
        mock_db = AsyncMock()
        mock_db.commit.side_effect = Exception("Database error")
        mock_db.rollback = AsyncMock()
        
        with pytest.raises(DocumentProcessingError, match="Failed to store chunks"):
            await processor._store_chunks(mock_db, 123456789, chunks)
        
        assert mock_db.rollback.called
    
    @pytest.mark.asyncio
    async def test_get_document(self, processor):
        """Test getting document from database"""
        # Create a mock document for this test
        test_doc = MagicMock(spec=Document)
        test_doc.id = 123456789
        test_doc.name = "test.txt"
        
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = test_doc
        mock_db.execute.return_value = mock_result
        
        with patch('sqlalchemy.select'):
            document = await processor._get_document(mock_db, 123456789)
            
            assert document == test_doc
            assert mock_db.execute.called
    
    @pytest.mark.asyncio
    async def test_update_document_status(self, processor, mock_document):
        """Test updating document status"""
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        await processor._update_document_status(mock_db, mock_document, "completed", "Processing finished")
        
        assert mock_document.status == "completed"
        assert mock_document.document_metadata['processing_status'] == "completed"
        assert mock_document.document_metadata['last_processing_message'] == "Processing finished"
        assert 'last_processed_at' in mock_document.document_metadata
        assert mock_db.commit.called
        assert mock_db.refresh.called
    
    @pytest.mark.asyncio
    async def test_update_document_metadata(self, processor, mock_document):
        """Test updating document metadata"""
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        extraction_result = {
            'text': 'test content',
            'file_hash': 'abc123',
            'metadata': {'encoding': 'utf-8'}
        }
        
        await processor._update_document_metadata(mock_db, mock_document, extraction_result, 5)
        
        assert mock_document.document_metadata['file_hash'] == 'abc123'
        assert mock_document.document_metadata['chunk_count'] == 5
        assert mock_document.document_metadata['character_count'] == len('test content')
        assert 'processing_completed_at' in mock_document.document_metadata
        assert mock_document.document_metadata['extraction_metadata'] == {'encoding': 'utf-8'}
        assert mock_db.commit.called
        assert mock_db.refresh.called
    
    @pytest.mark.asyncio
    async def test_process_document_success(self, processor, temp_dir):
        """Test successful document processing"""
        # Create test file
        test_file = temp_dir / "test.txt"
        content = "This is test content for processing."
        test_file.write_text(content)
        
        document_id = 123456789
        
        # Mock all dependencies
        mock_extraction_result = {
            'text': content,
            'file_hash': 'abc123',
            'file_size': len(content),
            'file_type': 'txt',
            'metadata': {'encoding': 'utf-8'}
        }
        
        mock_chunks = [
            {
                'chunk_index': 0,
                'content': content,
                'start_char': 0,
                'end_char': len(content),
                'token_count': 8
            }
        ]
        
        with patch.object(processor, '_get_document', return_value=mock_document) as mock_get_doc, \
             patch.object(processor, '_update_document_status') as mock_update_status, \
             patch.object(processor, '_extract_text', return_value=mock_extraction_result) as mock_extract, \
             patch.object(processor, '_create_chunks', return_value=mock_chunks) as mock_chunk, \
             patch.object(processor, '_store_chunks', return_value=[MagicMock()]) as mock_store, \
             patch.object(processor, '_update_document_metadata') as mock_update_meta, \
             patch('app.services.document_processor.get_db') as mock_get_db:
            
            # Mock database session
            mock_db = AsyncMock()
            mock_get_db.return_value.__aiter__.return_value = [mock_db]
            
            result = await processor.process_document(document_id, str(test_file))
            
            assert result['success'] is True
            assert result['document_id'] == document_id
            assert result['chunks_created'] == 1
            assert result['file_hash'] == 'abc123'
            
            # Verify all steps were called
            assert mock_get_doc.called
            assert mock_update_status.call_count >= 3  # Multiple status updates
            assert mock_extract.called
            assert mock_chunk.called
            assert mock_store.called
            assert mock_update_meta.called
    
    @pytest.mark.asyncio
    async def test_process_document_not_found(self, processor):
        """Test processing non-existent document"""
        with patch.object(processor, '_get_document', return_value=None), \
             patch('app.services.document_processor.get_db') as mock_get_db:
            
            mock_db = AsyncMock()
            mock_get_db.return_value.__aiter__.return_value = [mock_db]
            
            with pytest.raises(DocumentProcessingError, match="Document .* not found"):
                await processor.process_document(999, "test.txt")
    
    @pytest.mark.asyncio
    async def test_process_document_extraction_error(self, processor, mock_document):
        """Test processing with extraction error"""
        with patch.object(processor, '_get_document', return_value=mock_document), \
             patch.object(processor, '_update_document_status') as mock_update_status, \
             patch.object(processor, '_extract_text', side_effect=Exception("Extraction failed")), \
             patch('app.services.document_processor.get_db') as mock_get_db:
            
            mock_db = AsyncMock()
            mock_get_db.return_value.__aiter__.return_value = [mock_db]
            
            with pytest.raises(DocumentProcessingError, match="Failed to process document"):
                await processor.process_document(123456789, "test.txt")
            
            # Should update status to failed
            mock_update_status.assert_called()
    
    def test_check_duplicate_placeholder(self, processor):
        """Test duplicate check placeholder"""
        # Currently returns None (not implemented)
        result = processor.check_duplicate("abc123")
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__])