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
    try:
        # Update task state
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Starting URL processing', 'progress': 0}
        )
        
        # TODO: Implement URL processing
        # This would involve web scraping and then text processing
        # For now, return a placeholder
        
        return {
            'status': 'SUCCESS',
            'result': {
                'success': True,
                'document_id': document_id,
                'url': url,
                'message': 'URL processing not yet implemented'
            }
        }
        
    except Exception as e:
        # Update task state to failure
        self.update_state(
            state='FAILURE',
            meta={'status': 'URL processing failed', 'error': str(e)}
        )
        
        raise self.retry(exc=e, countdown=60, max_retries=3)