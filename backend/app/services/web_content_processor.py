"""
Web content processing service for cleaning HTML and extracting metadata
"""

import re
from datetime import datetime
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Comment, NavigableString


class WebContentProcessor:
    """Service for processing web content and extracting metadata"""
    
    def __init__(self):
        # Tags to remove completely (including content)
        self.remove_tags = {
            'script', 'style', 'noscript', 'iframe', 'embed', 'object',
            'applet', 'form', 'input', 'button', 'select', 'textarea',
            'nav', 'aside', 'footer', 'header', 'menu'
        }
        
        # Tags to remove but keep content
        self.unwrap_tags = {
            'span', 'div', 'section', 'article', 'main', 'figure',
            'figcaption', 'details', 'summary'
        }
        
        # Block-level tags that should preserve structure
        self.block_tags = {
            'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote',
            'pre', 'code', 'ul', 'ol', 'li', 'dl', 'dt', 'dd',
            'table', 'tr', 'td', 'th', 'thead', 'tbody', 'tfoot'
        }
        
        # Inline tags to preserve
        self.inline_tags = {
            'a', 'strong', 'b', 'em', 'i', 'u', 'mark', 'small',
            'del', 'ins', 'sub', 'sup', 'abbr', 'cite', 'q'
        }
    
    async def process_content(
        self, 
        html_content: str, 
        url: str, 
        response_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process HTML content and extract clean text with metadata
        
        Args:
            html_content: Raw HTML content
            url: Source URL
            response_metadata: Metadata from HTTP response
            
        Returns:
            Processed content with text and metadata
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract metadata first (before cleaning)
        metadata = await self._extract_metadata(soup, url, response_metadata)
        
        # Clean and extract text
        cleaned_text = await self._clean_and_extract_text(soup)
        
        return {
            'text': cleaned_text,
            'metadata': metadata
        }
    
    async def _extract_metadata(
        self, 
        soup: BeautifulSoup, 
        url: str, 
        response_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Extract comprehensive metadata from HTML"""
        metadata = {
            'url': url,
            'domain': urlparse(url).netloc,
            'scraped_at': datetime.utcnow().isoformat(),
            'content_type': 'text/html'
        }
        
        # Add response metadata if available
        if response_metadata:
            metadata.update({
                'status_code': response_metadata.get('status_code'),
                'content_length': response_metadata.get('content_length'),
                'response_headers': response_metadata.get('headers', {})
            })
        
        # Extract title
        title_tag = soup.find('title')
        if title_tag:
            metadata['title'] = self._clean_text(title_tag.get_text())
        
        # Extract meta tags
        meta_tags = soup.find_all('meta')
        for meta in meta_tags:
            name = meta.get('name', '').lower()
            property_attr = meta.get('property', '').lower()
            content = meta.get('content', '').strip()
            
            if not content:
                continue
            
            # Standard meta tags
            if name == 'description':
                metadata['description'] = content
            elif name == 'keywords':
                metadata['keywords'] = [k.strip() for k in content.split(',')]
            elif name == 'author':
                metadata['author'] = content
            elif name == 'robots':
                metadata['robots'] = content
            elif name == 'language':
                metadata['language'] = content
            elif name == 'generator':
                metadata['generator'] = content
            
            # Open Graph tags
            elif property_attr.startswith('og:'):
                og_key = property_attr[3:]  # Remove 'og:' prefix
                metadata[f'og_{og_key}'] = content
            
            # Twitter Card tags
            elif name.startswith('twitter:'):
                twitter_key = name[8:]  # Remove 'twitter:' prefix
                metadata[f'twitter_{twitter_key}'] = content
            
            # Article tags
            elif property_attr.startswith('article:'):
                article_key = property_attr[8:]  # Remove 'article:' prefix
                metadata[f'article_{article_key}'] = content
        
        # Extract structured data (JSON-LD)
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        if json_ld_scripts:
            structured_data = []
            for script in json_ld_scripts:
                try:
                    import json
                    data = json.loads(script.string)
                    structured_data.append(data)
                except:
                    continue
            if structured_data:
                metadata['structured_data'] = structured_data
        
        # Extract canonical URL
        canonical = soup.find('link', rel='canonical')
        if canonical and canonical.get('href'):
            metadata['canonical_url'] = canonical['href']
        
        # Extract language from html tag
        html_tag = soup.find('html')
        if html_tag and html_tag.get('lang'):
            metadata['html_lang'] = html_tag['lang']
        
        # Extract publication date from various sources
        pub_date = self._extract_publication_date(soup)
        if pub_date:
            metadata['published_date'] = pub_date
        
        # Extract headings structure
        headings = self._extract_headings(soup)
        if headings:
            metadata['headings'] = headings
        
        # Extract links
        links = self._extract_links_metadata(soup, url)
        if links:
            metadata['links'] = links
        
        # Extract images
        images = self._extract_images_metadata(soup, url)
        if images:
            metadata['images'] = images
        
        # Content statistics
        text_content = soup.get_text()
        metadata['word_count'] = len(text_content.split())
        metadata['char_count'] = len(text_content)
        
        return metadata
    
    async def _clean_and_extract_text(self, soup: BeautifulSoup) -> str:
        """Clean HTML and extract readable text"""
        # Remove comments
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
        
        # Remove unwanted tags completely
        for tag_name in self.remove_tags:
            for tag in soup.find_all(tag_name):
                tag.decompose()
        
        # Remove empty tags
        self._remove_empty_tags(soup)
        
        # Extract text with structure preservation
        text_parts = []
        self._extract_text_recursive(soup, text_parts)
        
        # Join and clean text
        full_text = '\n'.join(text_parts)
        cleaned_text = self._clean_text(full_text)
        
        return cleaned_text
    
    def _extract_text_recursive(self, element, text_parts: List[str], depth: int = 0):
        """Recursively extract text while preserving structure"""
        if isinstance(element, NavigableString):
            text = str(element).strip()
            if text:
                text_parts.append(text)
            return
        
        if not hasattr(element, 'name'):
            return
        
        tag_name = element.name.lower()
        
        # Skip unwanted tags
        if tag_name in self.remove_tags:
            return
        
        # Handle block-level tags
        if tag_name in self.block_tags:
            # Add spacing before block elements (except at start)
            if text_parts and not text_parts[-1].endswith('\n'):
                text_parts.append('\n')
            
            # Process children
            for child in element.children:
                self._extract_text_recursive(child, text_parts, depth + 1)
            
            # Add spacing after block elements
            if text_parts and not text_parts[-1].endswith('\n'):
                text_parts.append('\n')
        
        # Handle list items specially
        elif tag_name == 'li':
            if text_parts and not text_parts[-1].endswith('\n'):
                text_parts.append('\n')
            text_parts.append('• ')  # Add bullet point
            
            for child in element.children:
                self._extract_text_recursive(child, text_parts, depth + 1)
            
            if text_parts and not text_parts[-1].endswith('\n'):
                text_parts.append('\n')
        
        # Handle inline tags
        elif tag_name in self.inline_tags:
            for child in element.children:
                self._extract_text_recursive(child, text_parts, depth + 1)
        
        # Handle other tags (unwrap)
        else:
            for child in element.children:
                self._extract_text_recursive(child, text_parts, depth + 1)
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove excessive newlines
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # Clean up spacing around punctuation
        text = re.sub(r'\s+([,.!?;:])', r'\1', text)
        text = re.sub(r'([,.!?;:])\s+', r'\1 ', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def _remove_empty_tags(self, soup: BeautifulSoup):
        """Remove empty tags that don't contribute content"""
        # Tags that should be removed if empty
        removable_if_empty = {
            'p', 'div', 'span', 'section', 'article', 'aside',
            'header', 'footer', 'main', 'figure', 'figcaption'
        }
        
        changed = True
        while changed:
            changed = False
            for tag_name in removable_if_empty:
                for tag in soup.find_all(tag_name):
                    if not tag.get_text(strip=True) and not tag.find_all(['img', 'video', 'audio', 'iframe']):
                        tag.decompose()
                        changed = True
    
    def _extract_publication_date(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract publication date from various sources"""
        # Try meta tags first
        date_selectors = [
            ('meta', {'name': 'article:published_time'}),
            ('meta', {'property': 'article:published_time'}),
            ('meta', {'name': 'publishdate'}),
            ('meta', {'name': 'date'}),
            ('meta', {'name': 'DC.date'}),
            ('meta', {'name': 'DC.date.created'}),
            ('time', {'datetime': True}),
            ('time', {'pubdate': True}),
        ]
        
        for tag_name, attrs in date_selectors:
            tag = soup.find(tag_name, attrs)
            if tag:
                date_value = tag.get('content') or tag.get('datetime') or tag.get_text()
                if date_value:
                    return self._normalize_date(date_value.strip())
        
        # Try structured data
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_ld_scripts:
            try:
                import json
                data = json.loads(script.string)
                if isinstance(data, dict):
                    date_published = data.get('datePublished')
                    if date_published:
                        return self._normalize_date(date_published)
            except:
                continue
        
        return None
    
    def _normalize_date(self, date_str: str) -> Optional[str]:
        """Normalize date string to ISO format"""
        try:
            from dateutil import parser
            parsed_date = parser.parse(date_str)
            return parsed_date.isoformat()
        except:
            return date_str  # Return original if parsing fails
    
    def _extract_headings(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract heading structure"""
        headings = []
        for i in range(1, 7):  # h1 to h6
            for heading in soup.find_all(f'h{i}'):
                text = self._clean_text(heading.get_text())
                if text:
                    headings.append({
                        'level': i,
                        'text': text,
                        'id': heading.get('id')
                    })
        return headings
    
    def _extract_links_metadata(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """Extract links metadata"""
        links = []
        for link in soup.find_all('a', href=True):
            href = link['href'].strip()
            text = self._clean_text(link.get_text())
            title = link.get('title', '').strip()
            
            if href and not href.startswith('#'):
                from urllib.parse import urljoin
                absolute_url = urljoin(base_url, href)
                links.append({
                    'url': absolute_url,
                    'text': text,
                    'title': title
                })
        
        return links[:50]  # Limit to first 50 links
    
    def _extract_images_metadata(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """Extract images metadata"""
        images = []
        for img in soup.find_all('img', src=True):
            src = img['src'].strip()
            alt = img.get('alt', '').strip()
            title = img.get('title', '').strip()
            
            if src:
                from urllib.parse import urljoin
                absolute_url = urljoin(base_url, src)
                images.append({
                    'url': absolute_url,
                    'alt': alt,
                    'title': title
                })
        
        return images[:20]  # Limit to first 20 images