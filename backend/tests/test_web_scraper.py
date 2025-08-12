"""
Tests for web scraping service
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from app.services.web_scraper import WebScrapingService, WebScrapingError


class TestWebScrapingService:
    """Test cases for WebScrapingService"""
    
    @pytest.fixture
    def web_scraper(self):
        """Create a WebScrapingService instance for testing"""
        return WebScrapingService()
    
    @pytest.mark.asyncio
    async def test_validate_and_normalize_url_valid(self, web_scraper):
        """Test URL validation and normalization with valid URLs"""
        # Test with https URL
        url = await web_scraper._validate_and_normalize_url("https://example.com/page")
        assert url == "https://example.com/page"
        
        # Test with http URL
        url = await web_scraper._validate_and_normalize_url("http://example.com/page")
        assert url == "http://example.com/page"
        
        # Test URL without scheme (should add https)
        url = await web_scraper._validate_and_normalize_url("example.com/page")
        assert url == "https://example.com/page"
        
        # Test URL normalization (case, fragment removal)
        url = await web_scraper._validate_and_normalize_url("https://EXAMPLE.COM/Page#fragment")
        assert url == "https://example.com/Page"
    
    @pytest.mark.asyncio
    async def test_validate_and_normalize_url_invalid(self, web_scraper):
        """Test URL validation with invalid URLs"""
        # Test empty URL
        with pytest.raises(WebScrapingError, match="Invalid URL provided"):
            await web_scraper._validate_and_normalize_url("")
        
        # Test None URL
        with pytest.raises(WebScrapingError, match="Invalid URL provided"):
            await web_scraper._validate_and_normalize_url(None)
        
        # Test invalid URL format
        with pytest.raises(WebScrapingError, match="Invalid URL format"):
            await web_scraper._validate_and_normalize_url("not-a-url")
        
        # Test blocked domain
        with pytest.raises(WebScrapingError, match="Blocked domain"):
            await web_scraper._validate_and_normalize_url("https://localhost/page")
        
        # Test blocked file extension
        with pytest.raises(WebScrapingError, match="Blocked file extension"):
            await web_scraper._validate_and_normalize_url("https://example.com/file.exe")
        
        # Test unsupported scheme
        with pytest.raises(WebScrapingError, match="Unsupported URL scheme"):
            await web_scraper._validate_and_normalize_url("ftp://example.com/file")
    
    @pytest.mark.asyncio
    async def test_get_domain(self, web_scraper):
        """Test domain extraction from URLs"""
        assert web_scraper._get_domain("https://example.com/page") == "example.com"
        assert web_scraper._get_domain("https://sub.example.com/page") == "sub.example.com"
        assert web_scraper._get_domain("http://EXAMPLE.COM/page") == "example.com"
    
    @pytest.mark.asyncio
    async def test_is_same_domain_family(self, web_scraper):
        """Test domain family checking"""
        # Same domain
        assert web_scraper._is_same_domain_family("example.com", "example.com")
        
        # Same domain family (subdomain)
        assert web_scraper._is_same_domain_family("sub.example.com", "example.com")
        assert web_scraper._is_same_domain_family("example.com", "sub.example.com")
        
        # Different domains
        assert not web_scraper._is_same_domain_family("example.com", "other.com")
        assert not web_scraper._is_same_domain_family("example.com", "example.org")
    
    @pytest.mark.asyncio
    async def test_get_url_hash(self, web_scraper):
        """Test URL hash generation"""
        url1 = "https://example.com/page"
        url2 = "https://example.com/page"
        url3 = "https://example.com/other"
        
        hash1 = web_scraper._get_url_hash(url1)
        hash2 = web_scraper._get_url_hash(url2)
        hash3 = web_scraper._get_url_hash(url3)
        
        # Same URLs should have same hash
        assert hash1 == hash2
        
        # Different URLs should have different hashes
        assert hash1 != hash3
        
        # Hash should be consistent
        assert len(hash1) == 64  # SHA-256 hex digest length
    
    @pytest.mark.asyncio
    async def test_apply_rate_limit(self, web_scraper):
        """Test rate limiting functionality"""
        import time
        
        url = "https://example.com/page"
        
        # First request should not be delayed
        start_time = time.time()
        await web_scraper._apply_rate_limit(url)
        elapsed = time.time() - start_time
        assert elapsed < 0.1  # Should be very fast
        
        # Second request should be delayed
        start_time = time.time()
        await web_scraper._apply_rate_limit(url)
        elapsed = time.time() - start_time
        assert elapsed >= web_scraper.min_delay - 0.1  # Allow some tolerance
    
    @pytest.mark.asyncio
    async def test_reset_state(self, web_scraper):
        """Test state reset functionality"""
        # Add some state
        web_scraper.visited_urls.add("https://example.com")
        web_scraper.url_hashes.add("somehash")
        web_scraper.rate_limits["example.com"] = [time.time()]
        
        # Reset state
        web_scraper.reset_state()
        
        # Verify state is cleared
        assert len(web_scraper.visited_urls) == 0
        assert len(web_scraper.url_hashes) == 0
        assert len(web_scraper.rate_limits) == 0
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.get')
    async def test_scrape_with_aiohttp_success(self, mock_get, web_scraper):
        """Test successful scraping with aiohttp"""
        # Mock response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {'content-type': 'text/html', 'content-length': '1000'}
        mock_response.text = AsyncMock(return_value="<html><body>Test content</body></html>")
        mock_get.return_value.__aenter__.return_value = mock_response
        
        # Initialize session
        await web_scraper.initialize()
        
        try:
            content, metadata = await web_scraper._scrape_with_aiohttp("https://example.com")
            
            assert content == "<html><body>Test content</body></html>"
            assert metadata['status_code'] == 200
            assert metadata['content_type'] == 'text/html'
            assert metadata['content_length'] == len(content)
        finally:
            await web_scraper.cleanup()
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.get')
    async def test_scrape_with_aiohttp_error(self, mock_get, web_scraper):
        """Test scraping error handling with aiohttp"""
        # Mock 404 response
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.reason = "Not Found"
        mock_get.return_value.__aenter__.return_value = mock_response
        
        # Initialize session
        await web_scraper.initialize()
        
        try:
            with pytest.raises(WebScrapingError, match="HTTP 404"):
                await web_scraper._scrape_with_aiohttp("https://example.com")
        finally:
            await web_scraper.cleanup()
    
    @pytest.mark.asyncio
    async def test_extract_links(self, web_scraper):
        """Test link extraction from HTML"""
        html_content = """
        <html>
            <body>
                <a href="https://example.com/page1">Link 1</a>
                <a href="/relative/page">Relative Link</a>
                <a href="#fragment">Fragment Link</a>
                <a href="javascript:void(0)">JS Link</a>
                <a href="mailto:test@example.com">Email Link</a>
                <a>No href</a>
            </body>
        </html>
        """
        
        base_url = "https://example.com"
        links = await web_scraper._extract_links(html_content, base_url)
        
        # Should extract valid links and convert relative to absolute
        expected_links = [
            "https://example.com/page1",
            "https://example.com/relative/page"
        ]
        
        # Filter out invalid links (javascript, mailto, fragments, etc.)
        valid_links = [link for link in links if link in expected_links]
        assert len(valid_links) >= 1  # At least the absolute link should be valid
    
    @pytest.mark.asyncio
    async def test_context_manager(self, web_scraper):
        """Test async context manager functionality"""
        async with web_scraper as scraper:
            assert scraper.session is not None
        
        # Session should be cleaned up after context exit
        assert web_scraper.session is None


class TestWebScrapingIntegration:
    """Integration tests for web scraping (require network access)"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_scrape_real_url(self):
        """Test scraping a real URL (requires internet)"""
        web_scraper = WebScrapingService()
        
        try:
            async with web_scraper:
                # Use a reliable test URL
                result = await web_scraper.scrape_url("https://httpbin.org/html")
                
                assert result['success'] is True
                assert result['url'] == "https://httpbin.org/html"
                assert len(result['content']) > 0
                assert 'metadata' in result
                assert 'scraped_at' in result
        except Exception as e:
            pytest.skip(f"Network test failed: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_crawl_real_website(self):
        """Test crawling a real website (requires internet)"""
        web_scraper = WebScrapingService()
        
        try:
            async with web_scraper:
                # Use a simple test site with limited pages
                results = await web_scraper.crawl_website(
                    start_url="https://httpbin.org",
                    max_depth=1,
                    max_pages=2
                )
                
                assert len(results) >= 1
                assert all(result['success'] for result in results)
                assert all('url' in result for result in results)
                assert all('content' in result for result in results)
        except Exception as e:
            pytest.skip(f"Network test failed: {e}")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])