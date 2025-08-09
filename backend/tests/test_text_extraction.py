"""
Tests for text extraction service
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.services.text_extraction import TextExtractor, TextExtractionError


class TestTextExtractor:
    """Test cases for TextExtractor"""
    
    @pytest.fixture
    def extractor(self):
        """Create TextExtractor instance"""
        return TextExtractor()
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    def test_extract_text_file_not_found(self, extractor):
        """Test extraction with non-existent file"""
        with pytest.raises(TextExtractionError, match="File not found"):
            extractor.extract_text("nonexistent.txt")
    
    def test_extract_text_file_too_large(self, extractor, temp_dir):
        """Test extraction with file too large"""
        # Create a large file
        large_file = temp_dir / "large.txt"
        with open(large_file, "w") as f:
            # Write more than MAX_FILE_SIZE
            f.write("x" * (TextExtractor.MAX_FILE_SIZE + 1))
        
        with pytest.raises(TextExtractionError, match="File too large"):
            extractor.extract_text(str(large_file))
    
    def test_extract_text_unsupported_type(self, extractor, temp_dir):
        """Test extraction with unsupported file type"""
        unsupported_file = temp_dir / "test.xyz"
        unsupported_file.write_text("test content")
        
        with pytest.raises(TextExtractionError, match="Unsupported file type"):
            extractor.extract_text(str(unsupported_file), "xyz")
    
    def test_extract_text_file_basic(self, extractor, temp_dir):
        """Test basic text file extraction"""
        text_file = temp_dir / "test.txt"
        content = "This is a test document.\nWith multiple lines."
        text_file.write_text(content, encoding='utf-8')
        
        result = extractor.extract_text(str(text_file), "txt")
        
        assert result['text'] == content
        assert result['file_type'] == 'txt'
        assert result['file_size'] == len(content.encode('utf-8'))
        assert 'file_hash' in result
        assert result['metadata']['encoding'] == 'utf-8'
        assert result['metadata']['line_count'] == 2
        assert result['metadata']['extraction_method'] == 'text'
    
    def test_extract_markdown_file(self, extractor, temp_dir):
        """Test markdown file extraction"""
        md_file = temp_dir / "test.md"
        content = "# Test Document\n\nThis is **markdown** content."
        md_file.write_text(content, encoding='utf-8')
        
        result = extractor.extract_text(str(md_file), "md")
        
        assert result['text'] == content
        assert result['file_type'] == 'md'
        assert result['metadata']['extraction_method'] == 'text'
    
    def test_extract_csv_file(self, extractor, temp_dir):
        """Test CSV file extraction"""
        csv_file = temp_dir / "test.csv"
        content = "Name,Age,City\nJohn,30,New York\nJane,25,Boston"
        csv_file.write_text(content, encoding='utf-8')
        
        result = extractor.extract_text(str(csv_file), "csv")
        
        assert "Name | Age | City" in result['text']
        assert "John | 30 | New York" in result['text']
        assert "Jane | 25 | Boston" in result['text']
        assert result['metadata']['row_count'] == 3
        assert result['metadata']['delimiter'] == ','
        assert result['metadata']['extraction_method'] == 'csv'
    
    def test_detect_file_type_by_extension(self, extractor, temp_dir):
        """Test file type detection by extension"""
        pdf_file = temp_dir / "test.pdf"
        pdf_file.write_bytes(b"fake pdf content")
        
        # Mock magic to return unknown MIME type
        with patch.object(extractor.mime_detector, 'from_file', return_value='application/octet-stream'):
            file_type = extractor._detect_file_type(pdf_file)
            assert file_type == 'pdf'
    
    def test_calculate_file_hash(self, extractor, temp_dir):
        """Test file hash calculation"""
        test_file = temp_dir / "test.txt"
        content = "test content"
        test_file.write_text(content)
        
        hash1 = extractor._calculate_file_hash(test_file)
        hash2 = extractor._calculate_file_hash(test_file)
        
        # Same file should produce same hash
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 produces 64-character hex string
    
    def test_extract_text_with_encoding_fallback(self, extractor, temp_dir):
        """Test text extraction with encoding fallback"""
        text_file = temp_dir / "test.txt"
        # Write content with latin-1 encoding
        content = "Café résumé naïve"
        with open(text_file, 'w', encoding='latin-1') as f:
            f.write(content)
        
        result = extractor.extract_text(str(text_file), "txt")
        
        assert result['text'] == content
        assert result['metadata']['encoding'] in ['utf-8', 'latin-1']
    
    @patch('app.services.text_extraction.pdfplumber')
    def test_extract_pdf_with_pdfplumber(self, mock_pdfplumber, extractor, temp_dir):
        """Test PDF extraction with pdfplumber"""
        pdf_file = temp_dir / "test.pdf"
        pdf_file.write_bytes(b"fake pdf")
        
        # Mock pdfplumber
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Page 1 content"
        mock_pdf.pages = [mock_page]
        mock_pdf.metadata = {'Title': 'Test PDF', 'Author': 'Test Author'}
        mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf
        
        result = extractor.extract_text(str(pdf_file), "pdf")
        
        assert result['text'] == "Page 1 content"
        assert result['metadata']['page_count'] == 1
        assert result['metadata']['extraction_method'] == 'pdfplumber'
        assert result['metadata']['title'] == 'Test PDF'
        assert result['metadata']['author'] == 'Test Author'
    
    @patch('app.services.text_extraction.DocxDocument')
    def test_extract_docx(self, mock_docx, extractor, temp_dir):
        """Test DOCX extraction"""
        docx_file = temp_dir / "test.docx"
        docx_file.write_bytes(b"fake docx")
        
        # Mock docx document
        mock_doc = MagicMock()
        mock_paragraph = MagicMock()
        mock_paragraph.text = "Test paragraph"
        mock_doc.paragraphs = [mock_paragraph]
        mock_doc.tables = []
        mock_doc.core_properties.title = "Test Document"
        mock_doc.core_properties.author = "Test Author"
        mock_docx.return_value = mock_doc
        
        result = extractor.extract_text(str(docx_file), "docx")
        
        assert result['text'] == "Test paragraph"
        assert result['metadata']['paragraph_count'] == 1
        assert result['metadata']['table_count'] == 0
        assert result['metadata']['extraction_method'] == 'python-docx'
        assert result['metadata']['title'] == 'Test Document'
        assert result['metadata']['author'] == 'Test Author'
    
    @patch('app.services.text_extraction.Presentation')
    def test_extract_pptx(self, mock_presentation, extractor, temp_dir):
        """Test PPTX extraction"""
        pptx_file = temp_dir / "test.pptx"
        pptx_file.write_bytes(b"fake pptx")
        
        # Mock presentation
        mock_prs = MagicMock()
        mock_slide = MagicMock()
        mock_shape = MagicMock()
        mock_shape.text = "Slide content"
        mock_slide.shapes = [mock_shape]
        mock_prs.slides = [mock_slide]
        mock_prs.core_properties.title = "Test Presentation"
        mock_presentation.return_value = mock_prs
        
        result = extractor.extract_text(str(pptx_file), "pptx")
        
        assert "Slide 1:" in result['text']
        assert "Slide content" in result['text']
        assert result['metadata']['slide_count'] == 1
        assert result['metadata']['extraction_method'] == 'python-pptx'
        assert result['metadata']['title'] == 'Test Presentation'
    
    @patch('app.services.text_extraction.load_workbook')
    def test_extract_xlsx(self, mock_load_workbook, extractor, temp_dir):
        """Test XLSX extraction"""
        xlsx_file = temp_dir / "test.xlsx"
        xlsx_file.write_bytes(b"fake xlsx")
        
        # Mock workbook
        mock_workbook = MagicMock()
        mock_sheet = MagicMock()
        mock_sheet.iter_rows.return_value = [
            ("Name", "Age"),
            ("John", 30),
            ("Jane", 25)
        ]
        mock_workbook.__getitem__.return_value = mock_sheet
        mock_workbook.sheetnames = ["Sheet1"]
        mock_workbook.properties.title = "Test Workbook"
        mock_load_workbook.return_value = mock_workbook
        
        result = extractor.extract_text(str(xlsx_file), "xlsx")
        
        assert "Sheet: Sheet1" in result['text']
        assert "Name | Age" in result['text']
        assert "John | 30" in result['text']
        assert result['metadata']['sheet_count'] == 1
        assert result['metadata']['total_rows'] == 3
        assert result['metadata']['extraction_method'] == 'openpyxl'
        assert result['metadata']['title'] == 'Test Workbook'
    
    def test_extract_csv_with_different_delimiter(self, extractor, temp_dir):
        """Test CSV extraction with semicolon delimiter"""
        csv_file = temp_dir / "test.csv"
        content = "Name;Age;City\nJohn;30;New York\nJane;25;Boston"
        csv_file.write_text(content, encoding='utf-8')
        
        result = extractor.extract_text(str(csv_file), "csv")
        
        assert "Name | Age | City" in result['text']
        assert result['metadata']['delimiter'] == ';'
    
    def test_extract_empty_file(self, extractor, temp_dir):
        """Test extraction from empty file"""
        empty_file = temp_dir / "empty.txt"
        empty_file.write_text("", encoding='utf-8')
        
        result = extractor.extract_text(str(empty_file), "txt")
        
        assert result['text'] == ""
        assert result['file_size'] == 0
        assert result['metadata']['line_count'] == 1  # Empty file still has 1 line
    
    def test_extraction_error_handling(self, extractor, temp_dir):
        """Test error handling during extraction"""
        text_file = temp_dir / "test.txt"
        text_file.write_text("test content")
        
        # Mock an extraction method to raise an exception
        with patch.object(extractor, '_extract_text_file', side_effect=Exception("Mock error")):
            with pytest.raises(TextExtractionError, match="Failed to extract text from txt file"):
                extractor.extract_text(str(text_file), "txt")


if __name__ == "__main__":
    pytest.main([__file__])