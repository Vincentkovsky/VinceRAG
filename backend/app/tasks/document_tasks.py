"""
Celery tasks for document processing
"""

import asyncio
from typing import Dict, Any

from ..core.celery_app import celery_app
from ..services.document_processor import document_processor, DocumentProcessingError


@celery_app.task(bind=True, name="process_document_task")
def process_document_task(self, document_id: int, file_path: str) -> Dict[str, Any]:
    """
    Celery task for processing documents in the background
    
    Args:
        document_id: Document ID from database
        file_path: Path to the uploaded file
        
    Returns:
        Processing result
    """
    try:
        # Update task state
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Starting document processing', 'progress': 0}
        )
        
        # Run async processing in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                document_processor.process_document(document_id, file_path)
            )
            
            # Clean up the uploaded file after successful processing
            document_processor.cleanup_file(file_path)
            
            return {
                'status': 'SUCCESS',
                'result': result
            }
            
        finally:
            loop.close()
            
    except DocumentProcessingError as e:
        # Clean up file on error
        document_processor.cleanup_file(file_path)
        
        # Update task state to failure
        self.update_state(
            state='FAILURE',
            meta={'status': 'Processing failed', 'error': str(e)}
        )
        
        raise self.retry(exc=e, countdown=60, max_retries=3)
    
    except Exception as e:
        # Clean up file on unexpected error
        document_processor.cleanup_file(file_path)
        
        # Update task state to failure
        self.update_state(
            state='FAILURE',
            meta={'status': 'Unexpected error', 'error': str(e)}
        )
        
        raise


@celery_app.task(bind=True, name="process_url_task")
def process_url_task(self, document_id: int, url: str, crawl_options: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Celery task for processing URLs in the background
    
    Args:
        document_id: Document ID from database
        url: URL to scrape
        crawl_options: Optional crawling configuration
        
    Returns:
        Processing result
    """
    from ..services.url_processor import url_processor, URLProcessingError
    
    try:
        # Update task state
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Starting URL processing', 'progress': 0}
        )
        
        # Create progress callback to update task state
        def progress_callback(progress_data: Dict[str, Any]):
            status = progress_data.get('status', 'processing')
            message = progress_data.get('message', 'Processing URL...')
            
            # Convert status to progress percentage
            progress_map = {
                'starting': 10,
                'scraping': 30,
                'chunking': 60,
                'storing': 80,
                'completed': 100,
                'failed': 0
            }
            progress = progress_map.get(status, 50)
            
            self.update_state(
                state='PROGRESS',
                meta={'status': message, 'progress': progress}
            )
        
        # Run async processing in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Determine if we should use Playwright based on crawl options
            use_playwright = crawl_options.get('use_playwright', False) if crawl_options else False
            
            result = loop.run_until_complete(
                url_processor.process_single_url(
                    url=url,
                    document_id=document_id,
                    use_playwright=use_playwright,
                    progress_callback=progress_callback
                )
            )
            
            return {
                'status': 'SUCCESS',
                'result': result
            }
            
        finally:
            loop.close()
            
    except URLProcessingError as e:
        # Update task state to failure
        self.update_state(
            state='FAILURE',
            meta={'status': 'URL processing failed', 'error': str(e)}
        )
        
        raise self.retry(exc=e, countdown=60, max_retries=3)
    
    except Exception as e:
        # Update task state to failure
        self.update_state(
            state='FAILURE',
            meta={'status': 'Unexpected error', 'error': str(e)}
        )
        
        raise


@celery_app.task(bind=True, name="crawl_website_task")
def crawl_website_task(
    self, 
    parent_document_id: int, 
    start_url: str, 
    crawl_options: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Celery task for crawling websites in the background
    
    Args:
        parent_document_id: Parent document ID for tracking the crawl
        start_url: Starting URL for crawling
        crawl_options: Crawling configuration
        
    Returns:
        Crawling result with list of processed documents
    """
    from ..services.url_processor import url_processor, URLProcessingError
    
    try:
        # Update task state
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Starting website crawl', 'progress': 0}
        )
        
        # Create progress callback to update task state
        def progress_callback(progress_data: Dict[str, Any]):
            status = progress_data.get('status', 'crawling')
            message = progress_data.get('message', 'Crawling website...')
            
            # Calculate progress based on crawl status
            if status == 'starting_crawl':
                progress = 5
            elif status == 'crawling':
                crawl_progress = progress_data.get('crawl_progress', {})
                processed = crawl_progress.get('processed', 0)
                total_found = crawl_progress.get('total_found', 1)
                progress = min(10 + (processed / total_found) * 60, 70)
            elif status == 'processing_page':
                current_page = progress_data.get('current_page', 1)
                total_pages = progress_data.get('total_pages', 1)
                progress = 70 + (current_page / total_pages) * 25
            elif status == 'crawl_completed':
                progress = 100
            elif status == 'crawl_failed':
                progress = 0
            else:
                progress = 50
            
            self.update_state(
                state='PROGRESS',
                meta={'status': message, 'progress': int(progress)}
            )
        
        # Run async processing in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Extract crawl parameters
            max_depth = crawl_options.get('max_depth', 2)
            max_pages = crawl_options.get('max_pages', 10)
            include_subdomains = crawl_options.get('include_subdomains', False)
            
            results = loop.run_until_complete(
                url_processor.crawl_website(
                    start_url=start_url,
                    max_depth=max_depth,
                    max_pages=max_pages,
                    include_subdomains=include_subdomains,
                    progress_callback=progress_callback
                )
            )
            
            # Count successful results
            successful_results = [r for r in results if r.get('success')]
            
            return {
                'status': 'SUCCESS',
                'result': {
                    'parent_document_id': parent_document_id,
                    'start_url': start_url,
                    'total_processed': len(successful_results),
                    'total_attempted': len(results),
                    'results': results
                }
            }
            
        finally:
            loop.close()
            
    except URLProcessingError as e:
        # Update task state to failure
        self.update_state(
            state='FAILURE',
            meta={'status': 'Website crawl failed', 'error': str(e)}
        )
        
        raise self.retry(exc=e, countdown=120, max_retries=2)  # Longer retry for crawls
    
    except Exception as e:
        # Update task state to failure
        self.update_state(
            state='FAILURE',
            meta={'status': 'Unexpected error', 'error': str(e)}
        )
        
        raise