"""
URL processing service that integrates web scraping with document processing pipeline
"""

import asyncio
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from .web_scraper import WebScrapingService, WebScrapingError
from .document_service import DocumentService
from ..models.document import Document, DocumentChunk
from ..core.database import get_db
from ..core.snowflake import generate_id


class URLProcessingError(Exception):
    """Custom exception for URL processing errors"""
    pass


class URLProcessor:
    """Service for processing URLs through the complete pipeline"""
    
    def __init__(self):
        self.web_scraper = WebScrapingService()
    
    async def process_single_url(
        self,
        url: str,
        document_id: int,
        use_playwright: bool = False,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Process a single URL through the complete pipeline
        
        Args:
            url: URL to process
            document_id: Document ID from database
            use_playwright: Whether to use Playwright for dynamic content
            progress_callback: Optional callback for progress updates
            
        Returns:
            Processing result with statistics
        """
        try:
            async with self.web_scraper:
                # Update progress
                if progress_callback:
                    await progress_callback({
                        'status': 'starting',
                        'message': f'Starting to scrape {url}',
                        'document_id': document_id
                    })
                
                # Get database session
                async for db in get_db():
                    # Get document from database
                    document = await self._get_document(db, document_id)
                    if not document:
                        raise URLProcessingError(f"Document {document_id} not found")
                    
                    # Update status to processing
                    await self._update_document_status(
                        db, document, "processing", "Starting web scraping"
                    )
                    
                    # Update progress
                    if progress_callback:
                        await progress_callback({
                            'status': 'scraping',
                            'message': f'Scraping content from {url}',
                            'document_id': document_id
                        })
                    
                    # Scrape URL
                    scrape_result = await self.web_scraper.scrape_url(
                        url, use_playwright=use_playwright
                    )
                    
                    # Update status
                    await self._update_document_status(
                        db, document, "processing", "Content scraped, creating chunks"
                    )
                    
                    # Update progress
                    if progress_callback:
                        await progress_callback({
                            'status': 'chunking',
                            'message': 'Creating text chunks',
                            'document_id': document_id,
                            'content_length': len(scrape_result['content'])
                        })
                    
                    # Create chunks
                    chunks = await self._create_chunks(scrape_result['content'])
                    
                    # Update status
                    await self._update_document_status(
                        db, document, "processing", 
                        f"Created {len(chunks)} chunks, storing in database"
                    )
                    
                    # Update progress
                    if progress_callback:
                        await progress_callback({
                            'status': 'storing',
                            'message': f'Storing {len(chunks)} chunks in database',
                            'document_id': document_id,
                            'chunks_count': len(chunks)
                        })
                    
                    # Store chunks in database
                    chunk_records = await self._store_chunks(db, document_id, chunks)
                    
                    # Update document metadata
                    await self._update_document_metadata(db, document, scrape_result, len(chunks))
                    
                    # Update final status
                    await self._update_document_status(
                        db, document, "completed", 
                        f"Processing completed with {len(chunks)} chunks"
                    )
                    
                    # Final progress update
                    if progress_callback:
                        await progress_callback({
                            'status': 'completed',
                            'message': f'Successfully processed {url}',
                            'document_id': document_id,
                            'chunks_created': len(chunks)
                        })
                    
                    return {
                        'success': True,
                        'document_id': document_id,
                        'url': scrape_result['url'],
                        'chunks_created': len(chunks),
                        'total_characters': len(scrape_result['content']),
                        'metadata': scrape_result['metadata'],
                        'scraped_at': scrape_result['scraped_at']
                    }
                    
        except WebScrapingError as e:
            # Update document status to failed
            try:
                async for db in get_db():
                    document = await self._get_document(db, document_id)
                    if document:
                        await self._update_document_status(db, document, "failed", str(e))
            except:
                pass
            
            if progress_callback:
                await progress_callback({
                    'status': 'failed',
                    'message': str(e),
                    'document_id': document_id
                })
            
            raise URLProcessingError(f"Web scraping failed: {str(e)}")
            
        except Exception as e:
            # Update document status to failed
            try:
                async for db in get_db():
                    document = await self._get_document(db, document_id)
                    if document:
                        await self._update_document_status(db, document, "failed", str(e))
            except:
                pass
            
            if progress_callback:
                await progress_callback({
                    'status': 'failed',
                    'message': str(e),
                    'document_id': document_id
                })
            
            raise URLProcessingError(f"Failed to process URL {url}: {str(e)}")
    
    async def crawl_website(
        self,
        start_url: str,
        max_depth: int = 2,
        max_pages: int = 10,
        include_subdomains: bool = False,
        progress_callback: Optional[Callable] = None
    ) -> List[Dict[str, Any]]:
        """
        Crawl a website and create documents for each page
        
        Args:
            start_url: Starting URL for crawling
            max_depth: Maximum crawl depth
            max_pages: Maximum pages to crawl
            include_subdomains: Whether to include subdomains
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of processing results
        """
        results = []
        
        try:
            async with self.web_scraper:
                # Reset scraper state for new crawl
                self.web_scraper.reset_state()
                
                # Update progress
                if progress_callback:
                    await progress_callback({
                        'status': 'starting_crawl',
                        'message': f'Starting website crawl from {start_url}',
                        'max_pages': max_pages,
                        'max_depth': max_depth
                    })
                
                # Crawl website
                crawl_results = await self.web_scraper.crawl_website(
                    start_url=start_url,
                    max_depth=max_depth,
                    max_pages=max_pages,
                    include_subdomains=include_subdomains,
                    progress_callback=self._create_crawl_progress_callback(progress_callback)
                )
                
                # Process each crawled page
                for i, crawl_result in enumerate(crawl_results):
                    try:
                        # Update progress
                        if progress_callback:
                            await progress_callback({
                                'status': 'processing_page',
                                'message': f'Processing page {i+1}/{len(crawl_results)}: {crawl_result["url"]}',
                                'current_page': i + 1,
                                'total_pages': len(crawl_results)
                            })
                        
                        # Create document for this page
                        async for db in get_db():
                            document = await self._create_url_document(
                                db, crawl_result['url'], crawl_result['metadata']
                            )
                            
                            # Process the scraped content
                            chunks = await self._create_chunks(crawl_result['content'])
                            chunk_records = await self._store_chunks(db, document.id, chunks)
                            
                            # Update document metadata and status
                            await self._update_document_metadata(db, document, crawl_result, len(chunks))
                            await self._update_document_status(
                                db, document, "completed", 
                                f"Crawl processing completed with {len(chunks)} chunks"
                            )
                            
                            results.append({
                                'success': True,
                                'document_id': document.id,
                                'url': crawl_result['url'],
                                'chunks_created': len(chunks),
                                'total_characters': len(crawl_result['content']),
                                'metadata': crawl_result['metadata']
                            })
                            
                            break  # Exit the async for loop
                    
                    except Exception as e:
                        # Log error but continue with other pages
                        results.append({
                            'success': False,
                            'url': crawl_result['url'],
                            'error': str(e)
                        })
                        
                        if progress_callback:
                            await progress_callback({
                                'status': 'page_error',
                                'message': f'Error processing {crawl_result["url"]}: {str(e)}',
                                'current_page': i + 1,
                                'total_pages': len(crawl_results)
                            })
                
                # Final progress update
                if progress_callback:
                    successful_results = [r for r in results if r.get('success')]
                    await progress_callback({
                        'status': 'crawl_completed',
                        'message': f'Crawl completed: {len(successful_results)}/{len(crawl_results)} pages processed successfully',
                        'total_processed': len(successful_results),
                        'total_attempted': len(crawl_results)
                    })
                
                return results
                
        except Exception as e:
            if progress_callback:
                await progress_callback({
                    'status': 'crawl_failed',
                    'message': f'Website crawl failed: {str(e)}'
                })
            
            raise URLProcessingError(f"Website crawl failed: {str(e)}")
    
    async def check_url_duplicate(self, url: str) -> Optional[int]:
        """
        Check if a URL has already been processed
        
        Args:
            url: URL to check
            
        Returns:
            Document ID if duplicate found, None otherwise
        """
        try:
            # Normalize URL for comparison
            async with self.web_scraper:
                normalized_url = await self.web_scraper._validate_and_normalize_url(url)
            
            # Generate URL hash
            url_hash = hashlib.sha256(normalized_url.encode()).hexdigest()
            
            async for db in get_db():
                from sqlalchemy import select, text
                
                # Query for documents with matching URL hash in metadata
                result = await db.execute(
                    select(Document.id)
                    .where(text("document_metadata->>'url_hash' = :hash"))
                    .params(hash=url_hash)
                )
                
                existing_doc = result.scalar_one_or_none()
                return existing_doc
                
        except Exception:
            # If duplicate check fails, allow processing to proceed
            return None
    
    def _create_crawl_progress_callback(self, main_callback: Optional[Callable]) -> Optional[Callable]:
        """Create a progress callback for crawling that forwards to main callback"""
        if not main_callback:
            return None
        
        async def crawl_progress_callback(progress_data: Dict[str, Any]):
            # Forward crawl progress to main callback with additional context
            await main_callback({
                'status': 'crawling',
                'crawl_progress': progress_data,
                'message': f'Crawling: {progress_data.get("current_url", "")}'
            })
        
        return crawl_progress_callback
    
    async def _create_chunks(self, text: str) -> List[Dict[str, Any]]:
        """Create text chunks using the same logic as document processor"""
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        
        if not text.strip():
            raise URLProcessingError("No text content to chunk")
        
        try:
            # Configure text splitter
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                length_function=len,
                separators=["\n\n", "\n", " ", ""]
            )
            
            # Run chunking in thread pool
            loop = asyncio.get_event_loop()
            chunks = await loop.run_in_executor(
                None,
                text_splitter.split_text,
                text
            )
            
            # Create chunk data with position information
            chunk_data = []
            current_pos = 0
            
            for i, chunk_text in enumerate(chunks):
                # Find the position of this chunk in the original text
                start_pos = text.find(chunk_text, current_pos)
                if start_pos == -1:
                    # Fallback: approximate position
                    start_pos = current_pos
                
                end_pos = start_pos + len(chunk_text)
                current_pos = end_pos
                
                # Estimate token count (rough approximation: 1 token ≈ 4 characters)
                token_count = len(chunk_text) // 4
                
                chunk_data.append({
                    'chunk_index': i,
                    'content': chunk_text,
                    'start_char': start_pos,
                    'end_char': end_pos,
                    'token_count': token_count
                })
            
            return chunk_data
            
        except Exception as e:
            raise URLProcessingError(f"Text chunking failed: {str(e)}")
    
    async def _store_chunks(self, db: AsyncSession, document_id: int, chunks: List[Dict[str, Any]]) -> List[DocumentChunk]:
        """Store chunks in database"""
        chunk_records = []
        
        try:
            for chunk_data in chunks:
                # Generate unique vector ID (same as chunk ID for consistency)
                chunk_id = generate_id()
                vector_id = str(chunk_id)
                
                chunk_record = DocumentChunk(
                    id=chunk_id,
                    document_id=document_id,
                    chunk_index=chunk_data['chunk_index'],
                    vector_id=vector_id,
                    content=chunk_data['content'],
                    start_char=chunk_data['start_char'],
                    end_char=chunk_data['end_char'],
                    token_count=chunk_data['token_count']
                )
                
                db.add(chunk_record)
                chunk_records.append(chunk_record)
            
            await db.commit()
            
            # Refresh all records to get generated fields
            for chunk in chunk_records:
                await db.refresh(chunk)
            
            return chunk_records
            
        except Exception as e:
            await db.rollback()
            raise URLProcessingError(f"Failed to store chunks: {str(e)}")
    
    async def _create_url_document(
        self, 
        db: AsyncSession, 
        url: str, 
        metadata: Dict[str, Any]
    ) -> Document:
        """Create a document record for a URL"""
        # Generate URL hash for duplicate detection
        url_hash = hashlib.sha256(url.encode()).hexdigest()
        
        # Prepare document metadata
        doc_metadata = {
            'url': url,
            'url_hash': url_hash,
            'title': metadata.get('title', ''),
            'description': metadata.get('description', ''),
            'domain': metadata.get('domain', ''),
            'scraped_at': metadata.get('scraped_at', datetime.utcnow().isoformat()),
            'content_type': metadata.get('content_type', 'text/html'),
            'word_count': metadata.get('word_count', 0),
            'char_count': metadata.get('char_count', 0)
        }
        
        # Add additional metadata if available
        for key in ['author', 'published_date', 'language', 'keywords']:
            if key in metadata:
                doc_metadata[key] = metadata[key]
        
        # Create document name from title or URL
        document_name = metadata.get('title', url)
        if len(document_name) > 200:
            document_name = document_name[:197] + "..."
        
        # Create document instance
        document = Document(
            id=generate_id(),
            name=document_name,
            type="url",
            status="processing",
            document_metadata=doc_metadata
        )
        
        db.add(document)
        await db.commit()
        await db.refresh(document)
        
        return document
    
    async def _get_document(self, db: AsyncSession, document_id: int) -> Optional[Document]:
        """Get document from database"""
        from sqlalchemy import select
        result = await db.execute(select(Document).where(Document.id == document_id))
        return result.scalar_one_or_none()
    
    async def _update_document_status(
        self, 
        db: AsyncSession, 
        document: Document, 
        status: str, 
        message: str = None
    ):
        """Update document processing status"""
        document.status = status
        document.updated_at = datetime.utcnow()
        
        # Update metadata with processing info
        if not document.document_metadata:
            document.document_metadata = {}
        
        document.document_metadata['processing_status'] = status
        document.document_metadata['last_processing_message'] = message
        document.document_metadata['last_processed_at'] = datetime.utcnow().isoformat()
        
        await db.commit()
        await db.refresh(document)
    
    async def _update_document_metadata(
        self, 
        db: AsyncSession, 
        document: Document, 
        scrape_result: Dict[str, Any], 
        chunk_count: int
    ):
        """Update document metadata with scraping results"""
        if not document.document_metadata:
            document.document_metadata = {}
        
        # Merge scraping metadata
        document.document_metadata.update({
            'chunk_count': chunk_count,
            'character_count': len(scrape_result['content']),
            'processing_completed_at': datetime.utcnow().isoformat(),
            'scraping_method': scrape_result.get('method', 'unknown'),
            'scraping_metadata': scrape_result['metadata']
        })
        
        await db.commit()
        await db.refresh(document)


# Global processor instance
url_processor = URLProcessor()