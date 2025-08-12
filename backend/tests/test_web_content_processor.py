"""
Tests for web content processor
"""

import pytest
from datetime import datetime

from app.services.web_content_processor import WebContentProcessor


class TestWebContentProcessor:
    """Test cases for WebContentProcessor"""
    
    @pytest.fixture
    def processor(self):
        """Create a WebContentProcessor instance for testing"""
        return WebContentProcessor()
    
    @pytest.mark.asyncio
    async def test_clean_text_basic(self, processor):
        """Test basic text cleaning"""
        # Test whitespace normalization
        text = "  Multiple   spaces   and\n\n\nnewlines  "
        cleaned = processor._clean_text(text)
        assert cleaned == "Multiple spaces and\n\nnewlines"
        
        # Test punctuation spacing
        text = "Hello , world ! How are you ?"
        cleaned = processor._clean_text(text)
        assert cleaned == "Hello, world! How are you?"
        
        # Test empty text
        assert processor._clean_text("") == ""
        assert processor._clean_text(None) == ""
    
    @pytest.mark.asyncio
    async def test_extract_metadata_basic(self, processor):
        """Test basic metadata extraction"""
        html = """
        <html lang="en">
            <head>
                <title>Test Page Title</title>
                <meta name="description" content="This is a test page description">
                <meta name="keywords" content="test, page, html">
                <meta name="author" content="Test Author">
                <link rel="canonical" href="https://example.com/canonical">
            </head>
            <body>
                <h1>Main Heading</h1>
                <p>Some content here.</p>
            </body>
        </html>
        """
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        metadata = await processor._extract_metadata(soup, "https://example.com/test", None)
        
        assert metadata['title'] == "Test Page Title"
        assert metadata['description'] == "This is a test page description"
        assert metadata['keywords'] == ["test", "page", "html"]
        assert metadata['author'] == "Test Author"
        assert metadata['canonical_url'] == "https://example.com/canonical"
        assert metadata['html_lang'] == "en"
        assert metadata['url'] == "https://example.com/test"
        assert metadata['domain'] == "example.com"
    
    @pytest.mark.asyncio
    async def test_extract_metadata_open_graph(self, processor):
        """Test Open Graph metadata extraction"""
        html = """
        <html>
            <head>
                <meta property="og:title" content="OG Title">
                <meta property="og:description" content="OG Description">
                <meta property="og:image" content="https://example.com/image.jpg">
                <meta property="og:url" content="https://example.com/og-url">
                <meta name="twitter:card" content="summary">
                <meta name="twitter:title" content="Twitter Title">
            </head>
            <body></body>
        </html>
        """
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        metadata = await processor._extract_metadata(soup, "https://example.com/test", None)
        
        assert metadata['og_title'] == "OG Title"
        assert metadata['og_description'] == "OG Description"
        assert metadata['og_image'] == "https://example.com/image.jpg"
        assert metadata['og_url'] == "https://example.com/og-url"
        assert metadata['twitter_card'] == "summary"
        assert metadata['twitter_title'] == "Twitter Title"
    
    @pytest.mark.asyncio
    async def test_extract_headings(self, processor):
        """Test heading structure extraction"""
        html = """
        <html>
            <body>
                <h1 id="main">Main Title</h1>
                <h2>Section 1</h2>
                <h3>Subsection 1.1</h3>
                <h2>Section 2</h2>
                <h4>Deep subsection</h4>
            </body>
        </html>
        """
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        headings = processor._extract_headings(soup)
        
        assert len(headings) == 5
        assert headings[0]['level'] == 1
        assert headings[0]['text'] == "Main Title"
        assert headings[0]['id'] == "main"
        assert headings[1]['level'] == 2
        assert headings[1]['text'] == "Section 1"
        assert headings[2]['level'] == 3
        assert headings[2]['text'] == "Subsection 1.1"
    
    @pytest.mark.asyncio
    async def test_extract_links_metadata(self, processor):
        """Test link metadata extraction"""
        html = """
        <html>
            <body>
                <a href="https://example.com/page1" title="Page 1">Link 1</a>
                <a href="/relative/page" title="Relative">Relative Link</a>
                <a href="#fragment">Fragment Link</a>
                <a href="">Empty Link</a>
                <a>No href</a>
            </body>
        </html>
        """
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        links = processor._extract_links_metadata(soup, "https://example.com")
        
        # Should extract valid links and convert relative to absolute
        assert len(links) >= 2
        
        # Check absolute link
        absolute_link = next((link for link in links if link['url'] == "https://example.com/page1"), None)
        assert absolute_link is not None
        assert absolute_link['text'] == "Link 1"
        assert absolute_link['title'] == "Page 1"
        
        # Check relative link (converted to absolute)
        relative_link = next((link for link in links if link['url'] == "https://example.com/relative/page"), None)
        assert relative_link is not None
        assert relative_link['text'] == "Relative Link"
        assert relative_link['title'] == "Relative"
    
    @pytest.mark.asyncio
    async def test_extract_images_metadata(self, processor):
        """Test image metadata extraction"""
        html = """
        <html>
            <body>
                <img src="https://example.com/image1.jpg" alt="Image 1" title="First Image">
                <img src="/relative/image.png" alt="Relative Image">
                <img src="data:image/gif;base64,R0lGOD..." alt="Data URL">
                <img alt="No src">
            </body>
        </html>
        """
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        images = processor._extract_images_metadata(soup, "https://example.com")
        
        # Should extract valid images and convert relative to absolute
        assert len(images) >= 2
        
        # Check absolute image
        absolute_image = next((img for img in images if img['url'] == "https://example.com/image1.jpg"), None)
        assert absolute_image is not None
        assert absolute_image['alt'] == "Image 1"
        assert absolute_image['title'] == "First Image"
        
        # Check relative image (converted to absolute)
        relative_image = next((img for img in images if img['url'] == "https://example.com/relative/image.png"), None)
        assert relative_image is not None
        assert relative_image['alt'] == "Relative Image"
    
    @pytest.mark.asyncio
    async def test_clean_and_extract_text_basic(self, processor):
        """Test basic text extraction and cleaning"""
        html = """
        <html>
            <head>
                <title>Page Title</title>
                <script>console.log('remove me');</script>
                <style>body { color: red; }</style>
            </head>
            <body>
                <h1>Main Heading</h1>
                <p>This is a paragraph with <strong>bold text</strong> and <em>italic text</em>.</p>
                <ul>
                    <li>List item 1</li>
                    <li>List item 2</li>
                </ul>
                <div>
                    <span>Nested content</span>
                </div>
                <!-- This is a comment -->
                <script>alert('also remove me');</script>
            </body>
        </html>
        """
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        text = await processor._clean_and_extract_text(soup)
        
        # Should extract text content without scripts, styles, comments
        assert "Main Heading" in text
        assert "This is a paragraph with bold text and italic text." in text
        assert "• List item 1" in text
        assert "• List item 2" in text
        assert "Nested content" in text
        
        # Should not contain removed elements
        assert "console.log" not in text
        assert "color: red" not in text
        assert "alert" not in text
        assert "This is a comment" not in text
    
    @pytest.mark.asyncio
    async def test_clean_and_extract_text_structure(self, processor):
        """Test text extraction preserves structure"""
        html = """
        <html>
            <body>
                <h1>Title</h1>
                <p>First paragraph.</p>
                <p>Second paragraph.</p>
                <blockquote>This is a quote.</blockquote>
                <pre>Preformatted text</pre>
            </body>
        </html>
        """
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        text = await processor._clean_and_extract_text(soup)
        
        # Should preserve paragraph breaks
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        assert "Title" in lines
        assert "First paragraph." in lines
        assert "Second paragraph." in lines
        assert "This is a quote." in lines
        assert "Preformatted text" in lines
    
    @pytest.mark.asyncio
    async def test_remove_empty_tags(self, processor):
        """Test removal of empty tags"""
        html = """
        <html>
            <body>
                <div>Content</div>
                <div></div>
                <p>   </p>
                <span>Text</span>
                <span></span>
                <div><img src="image.jpg"></div>
            </body>
        </html>
        """
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        processor._remove_empty_tags(soup)
        
        # Should keep tags with content or media
        remaining_divs = soup.find_all('div')
        assert len(remaining_divs) == 2  # One with text, one with image
        
        remaining_spans = soup.find_all('span')
        assert len(remaining_spans) == 1  # Only the one with text
        
        remaining_ps = soup.find_all('p')
        assert len(remaining_ps) == 0  # Empty p should be removed
    
    @pytest.mark.asyncio
    async def test_normalize_date(self, processor):
        """Test date normalization"""
        # Test ISO date
        result = processor._normalize_date("2024-01-15T10:30:00Z")
        assert "2024-01-15" in result
        
        # Test human readable date
        result = processor._normalize_date("January 15, 2024")
        assert result is not None
        
        # Test invalid date
        result = processor._normalize_date("not a date")
        assert result == "not a date"  # Should return original if parsing fails
    
    @pytest.mark.asyncio
    async def test_process_content_integration(self, processor):
        """Test complete content processing"""
        html = """
        <html lang="en">
            <head>
                <title>Test Article</title>
                <meta name="description" content="A test article">
                <meta name="author" content="Test Author">
                <meta property="og:title" content="OG Test Article">
            </head>
            <body>
                <article>
                    <h1>Article Title</h1>
                    <p>This is the first paragraph of the article.</p>
                    <h2>Section 1</h2>
                    <p>This is content in section 1.</p>
                    <ul>
                        <li>Point 1</li>
                        <li>Point 2</li>
                    </ul>
                </article>
                <script>console.log('remove me');</script>
            </body>
        </html>
        """
        
        url = "https://example.com/article"
        response_metadata = {
            'status_code': 200,
            'content_type': 'text/html',
            'content_length': len(html)
        }
        
        result = await processor.process_content(html, url, response_metadata)
        
        # Check text extraction
        text = result['text']
        assert "Article Title" in text
        assert "This is the first paragraph" in text
        assert "Section 1" in text
        assert "• Point 1" in text
        assert "• Point 2" in text
        assert "console.log" not in text
        
        # Check metadata extraction
        metadata = result['metadata']
        assert metadata['title'] == "Test Article"
        assert metadata['description'] == "A test article"
        assert metadata['author'] == "Test Author"
        assert metadata['og_title'] == "OG Test Article"
        assert metadata['url'] == url
        assert metadata['domain'] == "example.com"
        assert metadata['status_code'] == 200
        assert metadata['word_count'] > 0
        assert metadata['char_count'] > 0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])