"""
Document management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from ...core.database import get_db
from ...core.deps import get_current_active_user
from ...models.user import User
from ...schemas.document import (
    Document, DocumentCreate, DocumentUpdate, DocumentList, 
    URLRequest, ProcessingStatus, DocumentChunkList
)
from ...services.document_service import DocumentService

router = APIRouter()


@router.get("/", response_model=DocumentList)
async def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all documents"""
    documents, total = await DocumentService.list_documents(db, skip, limit)
    
    return DocumentList(
        documents=[Document.model_validate(doc) for doc in documents],
        total=total,
        page=(skip // limit) + 1,
        page_size=limit
    )


@router.post("/upload", response_model=Document)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Upload a new document"""
    from ...core.config import settings
    from ...services.document_processor import document_processor
    from ...tasks.document_tasks import process_document_task
    import hashlib
    
    # Validate file size
    if file.size and file.size > settings.max_file_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {settings.max_file_size // (1024*1024)}MB"
        )
    
    # Validate file type
    supported_types = {
        'application/pdf': 'pdf',
        'text/plain': 'txt',
        'text/markdown': 'md',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'pptx',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
        'text/csv': 'csv',
        'application/rtf': 'rtf'
    }
    
    # Determine file type
    doc_type = supported_types.get(file.content_type)
    if not doc_type:
        # Try to determine from filename extension
        if file.filename:
            extension = file.filename.split('.')[-1].lower()
            extension_map = {
                'pdf': 'pdf', 'txt': 'txt', 'md': 'md', 'docx': 'docx',
                'pptx': 'pptx', 'xlsx': 'xlsx', 'csv': 'csv', 'rtf': 'rtf'
            }
            doc_type = extension_map.get(extension)
    
    if not doc_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Supported types: PDF, DOCX, TXT, MD, PPTX, XLSX, CSV, RTF"
        )
    
    # Read file content
    file_content = await file.read()
    
    # Calculate file hash for duplicate detection
    file_hash = hashlib.sha256(file_content).hexdigest()
    
    # Check for duplicates using document processor
    duplicate_doc_id = await document_processor.check_duplicate(file_hash)
    if duplicate_doc_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Document with same content already exists (ID: {duplicate_doc_id})"
        )
    
    # Create document data
    document_data = DocumentCreate(
        name=file.filename or f"uploaded_file.{doc_type}",
        type=doc_type,
        size=len(file_content),
        metadata={
            'mimeType': file.content_type,
            'originalFileName': file.filename,
            'fileHash': file_hash,
            'uploadedBy': current_user.id
        }
    )
    
    # Create document record
    document = await DocumentService.create_document(db, document_data)
    
    # Save file to storage
    try:
        file_path = document_processor.save_uploaded_file(
            file_content, 
            file.filename or f"document_{document.id}.{doc_type}",
            document.id
        )
        
        # Queue document for background processing
        task = process_document_task.delay(document.id, file_path)
        
        # Update document metadata with task ID
        await DocumentService.update_document(
            db, 
            document.id, 
            DocumentUpdate(metadata={'taskId': task.id})
        )
        
    except Exception as e:
        # If file saving fails, delete the document record
        await DocumentService.delete_document(db, document.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )
    
    return Document.model_validate(document)


@router.post("/url", response_model=Document)
async def add_url(
    url_request: URLRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Add a URL for scraping"""
    from ...services.url_processor import url_processor
    from ...tasks.document_tasks import process_url_task
    
    # Check for duplicate URL
    duplicate_doc_id = await url_processor.check_url_duplicate(str(url_request.url))
    if duplicate_doc_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"URL already processed (Document ID: {duplicate_doc_id})"
        )
    
    document_data = DocumentCreate(
        name=str(url_request.url),
        type='url',
        url=url_request.url,
        metadata={
            'url': str(url_request.url),
            'crawlOptions': url_request.crawl_options.dict() if url_request.crawl_options else None,
            'addedBy': current_user.id
        }
    )
    
    document = await DocumentService.create_document(db, document_data)
    
    # Queue URL for scraping
    try:
        crawl_options = url_request.crawl_options.dict() if url_request.crawl_options else {}
        task = process_url_task.delay(document.id, str(url_request.url), crawl_options)
        
        # Update document metadata with task ID
        await DocumentService.update_document(
            db, 
            document.id, 
            DocumentUpdate(metadata={'taskId': task.id})
        )
        
    except Exception as e:
        # If task queuing fails, delete the document record
        await DocumentService.delete_document(db, document.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue URL processing: {str(e)}"
        )
    
    return Document.model_validate(document)


@router.post("/crawl", response_model=List[Document])
async def crawl_website(
    url_request: URLRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Crawl a website starting from a URL"""
    from ...tasks.document_tasks import crawl_website_task
    
    # Validate crawl options
    crawl_options = url_request.crawl_options
    if not crawl_options:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Crawl options are required for website crawling"
        )
    
    # Create a parent document to track the crawl operation
    document_data = DocumentCreate(
        name=f"Website Crawl: {url_request.url}",
        type='url',
        url=url_request.url,
        metadata={
            'url': str(url_request.url),
            'crawlOptions': crawl_options.dict(),
            'addedBy': current_user.id,
            'isCrawlParent': True
        }
    )
    
    parent_document = await DocumentService.create_document(db, document_data)
    
    # Queue website crawling
    try:
        task = crawl_website_task.delay(
            parent_document.id,
            str(url_request.url),
            crawl_options.dict()
        )
        
        # Update document metadata with task ID
        await DocumentService.update_document(
            db, 
            parent_document.id, 
            DocumentUpdate(metadata={'taskId': task.id})
        )
        
        # Return the parent document for now
        # The actual crawled documents will be created by the background task
        return [Document.model_validate(parent_document)]
        
    except Exception as e:
        # If task queuing fails, delete the document record
        await DocumentService.delete_document(db, parent_document.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue website crawling: {str(e)}"
        )


@router.get("/{document_id}", response_model=Document)
async def get_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific document"""
    document = await DocumentService.get_document(db, document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    return Document.model_validate(document)


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a document"""
    success = await DocumentService.delete_document(db, document_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    return {"message": "Document deleted successfully"}


@router.get("/{document_id}/chunks", response_model=DocumentChunkList)
async def get_document_chunks(
    document_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get chunks for a specific document"""
    from sqlalchemy import select, func
    from ...models.document import DocumentChunk
    from ...schemas.document import DocumentChunkList
    
    # Verify document exists
    document = await DocumentService.get_document(db, document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Get total count
    count_result = await db.execute(
        select(func.count(DocumentChunk.id)).where(DocumentChunk.document_id == document_id)
    )
    total = count_result.scalar()
    
    # Get chunks
    result = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
        .offset(skip)
        .limit(limit)
    )
    chunks = result.scalars().all()
    
    # Add document info to chunks
    chunk_list = []
    for chunk in chunks:
        chunk_dict = {
            'id': chunk.id,
            'document_id': chunk.document_id,
            'chunk_index': chunk.chunk_index,
            'vector_id': chunk.vector_id,
            'content': chunk.content,
            'start_char': chunk.start_char,
            'end_char': chunk.end_char,
            'token_count': chunk.token_count,
            'created_at': chunk.created_at,
            'document_name': document.name,
            'document_type': document.type
        }
        chunk_list.append(chunk_dict)
    
    return DocumentChunkList(
        chunks=chunk_list,
        total=total,
        page=(skip // limit) + 1,
        page_size=limit
    )


@router.get("/{document_id}/status", response_model=ProcessingStatus)
async def get_document_status(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get document processing status"""
    from ...core.celery_app import celery_app
    
    document = await DocumentService.get_document(db, document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Get task progress if available
    progress = None
    message = None
    
    if document.metadata and 'taskId' in document.metadata:
        task_id = document.metadata['taskId']
        try:
            task_result = celery_app.AsyncResult(task_id)
            if task_result.state == 'PROGRESS':
                task_info = task_result.info
                progress = task_info.get('progress', 0) / 100.0  # Convert to 0-1 range
                message = task_info.get('status', 'Processing...')
            elif task_result.state == 'FAILURE':
                message = f"Processing failed: {task_result.info.get('error', 'Unknown error')}"
        except Exception:
            pass  # Ignore task lookup errors
    
    # Use document metadata message if available
    if not message and document.metadata:
        message = document.metadata.get('last_processing_message')
    
    return ProcessingStatus(
        document_id=document.id,
        status=document.status,
        progress=progress,
        message=message,
        updated_at=document.updated_at or document.created_at
    )