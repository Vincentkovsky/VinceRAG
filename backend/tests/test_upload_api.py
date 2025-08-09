"""
Tests for document upload API
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from fastapi import UploadFile
import io

from app.main import app


class TestDocumentUploadAPI:
    """Test cases for document upload API"""
    
    def test_upload_endpoint_exists(self):
        """Test that upload endpoint exists"""
        client = TestClient(app)
        
        # Create a simple test file
        test_content = b"This is a test document content"
        test_file = io.BytesIO(test_content)
        
        # Mock authentication and database dependencies
        with patch('app.api.v1.documents.get_current_active_user') as mock_auth, \
             patch('app.api.v1.documents.get_db') as mock_db, \
             patch('app.services.document_processor.document_processor') as mock_processor:
            
            # Setup mocks
            mock_auth.return_value = MagicMock(id=1)
            mock_db.return_value.__aenter__.return_value = AsyncMock()
            mock_processor.check_duplicate = AsyncMock(return_value=None)
            mock_processor.save_uploaded_file.return_value = "/tmp/test_file.txt"
            
            # Mock document service
            with patch('app.api.v1.documents.DocumentService') as mock_service:
                mock_doc = MagicMock()
                mock_doc.id = 123456789
                mock_doc.name = "test.txt"
                mock_doc.type = "txt"
                mock_doc.status = "processing"
                mock_service.create_document = AsyncMock(return_value=mock_doc)
                mock_service.update_document = AsyncMock(return_value=mock_doc)
                
                # Mock Celery task
                with patch('app.api.v1.documents.process_document_task') as mock_task:
                    mock_task.delay.return_value = MagicMock(id='task-123')
                    
                    # Make request
                    response = client.post(
                        "/api/v1/documents/upload",
                        files={"file": ("test.txt", test_file, "text/plain")}
                    )
                    
                    # Should not fail with 500 error
                    assert response.status_code != 500
    
    def test_file_type_validation(self):
        """Test file type validation"""
        client = TestClient(app)
        
        # Create a file with unsupported type
        test_content = b"This is a test document content"
        test_file = io.BytesIO(test_content)
        
        # Mock authentication
        with patch('app.api.v1.documents.get_current_active_user') as mock_auth, \
             patch('app.api.v1.documents.get_db') as mock_db:
            
            mock_auth.return_value = MagicMock(id=1)
            mock_db.return_value.__aenter__.return_value = AsyncMock()
            
            # Make request with unsupported file type
            response = client.post(
                "/api/v1/documents/upload",
                files={"file": ("test.xyz", test_file, "application/unknown")}
            )
            
            # Should return 400 for unsupported file type
            assert response.status_code == 400
            assert "Unsupported file type" in response.json()["detail"]


if __name__ == "__main__":
    pytest.main([__file__])