"""
Web scraping service for URL processing and content extraction
"""

import asyncio
import hashlib
import re
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.robotparser import RobotFileParser

import aiohttp
import validators
import tldextract
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Browser, Page

from .web_content_processor import WebContentProcessor


class WebScrapingError(Exception):
    """Custom exception for web scraping errors"""
    pass


class WebScrapingService:
    """Service for web scraping with security, rate limiting, and content processing"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.content_processor = WebContentProcessor()
        
        # Configuration
        self.max_depth = 2
        self.max_pages = 10
        self.max_file_size = 50 * 1024 * 1024  # 50MB
        self.timeout = 30
        self.user_agent = "RAG-System-Bot/1.0 (+https://example.com/bot)"
        
        # Security settings
        self.allowed_schemes = {'http', 'https'}
        self.blocked_domains = {
            'localhost', '127.0.0.1', '0.0.0.0', '::1',
            'internal', 'intranet', 'private'
        }
        self.blocked_extensions = {
            '.exe', '.zip', '.rar', '.tar', '.gz', '.7z',
            '.dmg', '.pkg', '.deb', '.rpm', '.msi'
        }
        
        # Rate limiting (per domain)
        self.rate_limits: Dict[str, List[float]] = {}
        self.min_delay = 1.0  # Minimum delay between requests (seconds)
        
        # Caching
        self.robots_cache: Dict[str, RobotFileParser] = {}
        self.visited_urls: Set[str] = set()
        self.url_hashes: Set[str] = set()
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.cleanup()
    
    async def initialize(self):
        """Initialize HTTP session and browser"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={'User-Agent': self.user_agent},
                connector=aiohttp.TCPConnector(limit=10, limit_per_host=2)
            )
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
            self.session = None
        
        if self.browser:
            await self.browser.close()
            self.browser = None
        
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
    
    async def scrape_url(
        self, 
        url: str, 
        use_playwright: bool = False,
        extract_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        Scrape a single URL
        
        Args:
            url: URL to scrape
            use_playwright: Whether to use Playwright for dynamic content
            extract_metadata: Whether to extract page metadata
            
        Returns:
            Scraping result with content and metadata
        """
        # Validate and normalize URL
        normalized_url = await self._validate_and_normalize_url(url)
        
        # Check if already processed
        url_hash = self._get_url_hash(normalized_url)
        if url_hash in self.url_hashes:
            raise WebScrapingError(f"URL already processed: {normalized_url}")
        
        # Check robots.txt
        if not await self._check_robots_txt(normalized_url):
            raise WebScrapingError(f"Robots.txt disallows scraping: {normalized_url}")
        
        # Apply rate limiting
        await self._apply_rate_limit(normalized_url)
        
        try:
            if use_playwright:
                content, metadata = await self._scrape_with_playwright(normalized_url)
            else:
                content, metadata = await self._scrape_with_aiohttp(normalized_url)
            
            # Process content
            processed_content = await self.content_processor.process_content(
                content, normalized_url, metadata if extract_metadata else None
            )
            
            # Mark as processed
            self.visited_urls.add(normalized_url)
            self.url_hashes.add(url_hash)
            
            return {
                'url': normalized_url,
                'content': processed_content['text'],
                'metadata': processed_content['metadata'],
                'scraped_at': datetime.utcnow(),
                'method': 'playwright' if use_playwright else 'aiohttp',
                'success': True
            }
            
        except Exception as e:
            raise WebScrapingError(f"Failed to scrape {normalized_url}: {str(e)}")
    
    async def crawl_website(
        self,
        start_url: str,
        max_depth: Optional[int] = None,
        max_pages: Optional[int] = None,
        include_subdomains: bool = False,
        progress_callback: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """
        Crawl a website starting from a URL
        
        Args:
            start_url: Starting URL for crawling
            max_depth: Maximum crawl depth (default: self.max_depth)
            max_pages: Maximum pages to crawl (default: self.max_pages)
            include_subdomains: Whether to include subdomains
            progress_callback: Callback for progress updates
            
        Returns:
            List of scraping results
        """
        max_depth = max_depth or self.max_depth
        max_pages = max_pages or self.max_pages
        
        # Validate starting URL
        start_url = await self._validate_and_normalize_url(start_url)
        base_domain = self._get_domain(start_url)
        
        # Initialize crawling state
        urls_to_visit = [(start_url, 0)]  # (url, depth)
        results = []
        processed_count = 0
        
        while urls_to_visit and processed_count < max_pages:
            current_url, depth = urls_to_visit.pop(0)
            
            # Skip if already processed or too deep
            if current_url in self.visited_urls or depth > max_depth:
                continue
            
            # Check domain restrictions
            current_domain = self._get_domain(current_url)
            if not include_subdomains and current_domain != base_domain:
                continue
            elif include_subdomains and not self._is_same_domain_family(current_domain, base_domain):
                continue
            
            try:
                # Scrape current URL
                result = await self.scrape_url(current_url, use_playwright=False)
                results.append(result)
                processed_count += 1
                
                # Update progress
                if progress_callback:
                    await progress_callback({
                        'processed': processed_count,
                        'total_found': len(urls_to_visit) + processed_count,
                        'current_url': current_url,
                        'depth': depth
                    })
                
                # Extract links for next level
                if depth < max_depth:
                    links = await self._extract_links(result['content'], current_url)
                    for link in links:
                        if link not in self.visited_urls:
                            urls_to_visit.append((link, depth + 1))
                
                # Small delay between requests
                await asyncio.sleep(0.5)
                
            except WebScrapingError as e:
                # Log error but continue crawling
                if progress_callback:
                    await progress_callback({
                        'error': str(e),
                        'url': current_url,
                        'processed': processed_count
                    })
                continue
        
        return results
    
    async def _validate_and_normalize_url(self, url: str) -> str:
        """Validate and normalize URL"""
        if not url or not isinstance(url, str):
            raise WebScrapingError("Invalid URL provided")
        
        # Add scheme if missing
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Validate URL format
        if not validators.url(url):
            raise WebScrapingError(f"Invalid URL format: {url}")
        
        parsed = urlparse(url)
        
        # Check scheme
        if parsed.scheme not in self.allowed_schemes:
            raise WebScrapingError(f"Unsupported URL scheme: {parsed.scheme}")
        
        # Check for blocked domains
        domain = parsed.netloc.lower()
        if any(blocked in domain for blocked in self.blocked_domains):
            raise WebScrapingError(f"Blocked domain: {domain}")
        
        # Check for blocked file extensions
        path = parsed.path.lower()
        if any(path.endswith(ext) for ext in self.blocked_extensions):
            raise WebScrapingError(f"Blocked file extension: {path}")
        
        # Normalize URL
        normalized = urlunparse((
            parsed.scheme,
            parsed.netloc.lower(),
            parsed.path,
            parsed.params,
            parsed.query,
            ''  # Remove fragment
        ))
        
        return normalized
    
    async def _check_robots_txt(self, url: str) -> bool:
        """Check robots.txt compliance"""
        try:
            parsed = urlparse(url)
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
            
            # Check cache first
            if robots_url in self.robots_cache:
                rp = self.robots_cache[robots_url]
            else:
                rp = RobotFileParser()
                rp.set_url(robots_url)
                
                # Fetch robots.txt with timeout
                try:
                    async with self.session.get(robots_url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                        if response.status == 200:
                            robots_content = await response.text()
                            rp.set_url(robots_url)
                            for line in robots_content.split('\n'):
                                rp.read()  # This is a bit hacky, but works for basic parsing
                except:
                    # If robots.txt is not accessible, assume allowed
                    return True
                
                self.robots_cache[robots_url] = rp
            
            return rp.can_fetch(self.user_agent, url)
            
        except Exception:
            # If robots.txt check fails, assume allowed
            return True
    
    async def _apply_rate_limit(self, url: str):
        """Apply rate limiting per domain"""
        domain = self._get_domain(url)
        current_time = time.time()
        
        # Initialize domain rate limit tracking
        if domain not in self.rate_limits:
            self.rate_limits[domain] = []
        
        # Clean old timestamps (older than 60 seconds)
        self.rate_limits[domain] = [
            t for t in self.rate_limits[domain] 
            if current_time - t < 60
        ]
        
        # Check if we need to wait
        if self.rate_limits[domain]:
            last_request = max(self.rate_limits[domain])
            time_since_last = current_time - last_request
            
            if time_since_last < self.min_delay:
                wait_time = self.min_delay - time_since_last
                await asyncio.sleep(wait_time)
        
        # Record this request
        self.rate_limits[domain].append(time.time())
    
    async def _scrape_with_aiohttp(self, url: str) -> Tuple[str, Dict[str, Any]]:
        """Scrape URL using aiohttp for static content"""
        try:
            async with self.session.get(url) as response:
                # Check response status
                if response.status >= 400:
                    raise WebScrapingError(f"HTTP {response.status}: {response.reason}")
                
                # Check content type
                content_type = response.headers.get('content-type', '').lower()
                if not any(ct in content_type for ct in ['text/html', 'application/xhtml']):
                    raise WebScrapingError(f"Unsupported content type: {content_type}")
                
                # Check content length
                content_length = response.headers.get('content-length')
                if content_length and int(content_length) > self.max_file_size:
                    raise WebScrapingError(f"Content too large: {content_length} bytes")
                
                # Read content
                content = await response.text()
                
                # Basic metadata from response
                metadata = {
                    'status_code': response.status,
                    'content_type': content_type,
                    'content_length': len(content),
                    'headers': dict(response.headers)
                }
                
                return content, metadata
                
        except aiohttp.ClientError as e:
            raise WebScrapingError(f"Network error: {str(e)}")
    
    async def _scrape_with_playwright(self, url: str) -> Tuple[str, Dict[str, Any]]:
        """Scrape URL using Playwright for dynamic content"""
        if not self.playwright:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
        
        try:
            page = await self.browser.new_page()
            
            # Set user agent and viewport
            await page.set_user_agent(self.user_agent)
            await page.set_viewport_size({"width": 1280, "height": 720})
            
            # Navigate to page
            response = await page.goto(url, wait_until='networkidle', timeout=self.timeout * 1000)
            
            if not response or response.status >= 400:
                raise WebScrapingError(f"HTTP {response.status if response else 'No response'}")
            
            # Wait for content to load
            await page.wait_for_timeout(2000)
            
            # Get page content
            content = await page.content()
            
            # Get page metadata
            title = await page.title()
            metadata = {
                'status_code': response.status,
                'title': title,
                'url': page.url,
                'content_length': len(content)
            }
            
            await page.close()
            return content, metadata
            
        except Exception as e:
            raise WebScrapingError(f"Playwright error: {str(e)}")
    
    async def _extract_links(self, html_content: str, base_url: str) -> List[str]:
        """Extract links from HTML content"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            links = []
            
            for link in soup.find_all('a', href=True):
                href = link['href'].strip()
                if not href or href.startswith('#'):
                    continue
                
                # Convert relative URLs to absolute
                absolute_url = urljoin(base_url, href)
                
                try:
                    # Validate the extracted URL
                    normalized_url = await self._validate_and_normalize_url(absolute_url)
                    links.append(normalized_url)
                except WebScrapingError:
                    # Skip invalid URLs
                    continue
            
            return list(set(links))  # Remove duplicates
            
        except Exception:
            return []
    
    def _get_domain(self, url: str) -> str:
        """Extract domain from URL"""
        return urlparse(url).netloc.lower()
    
    def _is_same_domain_family(self, domain1: str, domain2: str) -> bool:
        """Check if two domains belong to the same family (considering subdomains)"""
        extract1 = tldextract.extract(domain1)
        extract2 = tldextract.extract(domain2)
        
        return (extract1.domain == extract2.domain and 
                extract1.suffix == extract2.suffix)
    
    def _get_url_hash(self, url: str) -> str:
        """Generate hash for URL to detect duplicates"""
        return hashlib.sha256(url.encode()).hexdigest()
    
    def reset_state(self):
        """Reset crawling state for new session"""
        self.visited_urls.clear()
        self.url_hashes.clear()
        self.rate_limits.clear()


# Global instance
web_scraper = WebScrapingService()