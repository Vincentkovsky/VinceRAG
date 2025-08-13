"""
API endpoints for chunk management and vector operations
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from ...core.database import get_db
from ...services.vector_service import chunk_storage_manager, VectorDatabaseError
from ...models.document import DocumentChunk, Document
from sqlalchemy import select

router = APIRouter()


class ChunkCreate(BaseModel):
    """Schema for creating chunks"""
    content: str = Field(..., min_length=1, max_length=10000)
    start_char: int = Field(default=0, ge=0)
    end_char: int = Field(..., gt=0)
    token_count: int = Field(default=0, ge=0)


class ChunkResponse(BaseModel):
    """Schema for chunk response"""
    id: int
    document_id: int
    chunk_index: int
    vector_id: str
    content: str
    start_char: int
    end_char: int
    token_count: int
    created_at: str
    document_name: Optional[str] = None
    document_type: Optional[str] = None
    similarity: Optional[float] = None

    class Config:
        from_attributes = True


class SimilaritySearchRequest(BaseModel):
    """Schema for similarity search request"""
    query: str = Field(..., min_length=1, max_length=1000)
    n_results: int = Field(default=10, ge=1, le=50)
    document_id: Optional[int] = None
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)


class SimilaritySearchResponse(BaseModel):
    """Schema for similarity search response"""
    results: List[Dict[str, Any]]
    total_results: int
    query: str
    similarity_threshold: float


class ChunkStatsResponse(BaseModel):
    """Schema for chunk statistics response"""
    vector_database: Dict[str, Any]
    embedding_model: str
    chunk_size: int
    chunk_overlap: int


@router.get("/chunks/{chunk_id}", response_model=ChunkResponse)
async def get_chunk(
    chunk_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific chunk by ID"""
    try:
        chunk = await chunk_storage_manager.get_chunk_by_id(db, chunk_id)
        if not chunk:
            raise HTTPException(status_code=404, detail="Chunk not found")
        
        # Get document info
        result = await db.execute(
            select(Document).where(Document.id == chunk.document_id)
        )
        document = result.scalar_one_or_none()
        
        response_data = ChunkResponse.model_validate(chunk)
        if document:
            response_data.document_name = document.name
            response_data.document_type = document.type
        
        return response_data
        
    except VectorDatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/{document_id}/chunks", response_model=List[ChunkResponse])
async def get_document_chunks(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100)
):
    """Get all chunks for a specific document"""
    try:
        # Verify document exists
        result = await db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Get chunks
        result = await db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
            .offset(skip)
            .limit(limit)
        )
        chunks = result.scalars().all()
        
        # Convert to response format
        response_chunks = []
        for chunk in chunks:
            chunk_data = ChunkResponse.model_validate(chunk)
            chunk_data.document_name = document.name
            chunk_data.document_type = document.type
            response_chunks.append(chunk_data)
        
        return response_chunks
        
    except VectorDatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chunks/search", response_model=SimilaritySearchResponse)
async def similarity_search(
    search_request: SimilaritySearchRequest
):
    """Perform similarity search across all chunks"""
    try:
        results = await chunk_storage_manager.similarity_search(
            query=search_request.query,
            n_results=search_request.n_results,
            document_id=search_request.document_id,
            similarity_threshold=search_request.similarity_threshold
        )
        
        return SimilaritySearchResponse(
            results=results,
            total_results=len(results),
            query=search_request.query,
            similarity_threshold=search_request.similarity_threshold
        )
        
    except VectorDatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))


class ChunkUpdateRequest(BaseModel):
    """Request model for updating chunk content"""
    content: str = Field(..., min_length=1, max_length=10000)


@router.put("/chunks/{chunk_id}", response_model=ChunkResponse)
async def update_chunk(
    chunk_id: int,
    request: ChunkUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Update chunk content and re-embed"""
    try:
        updated_chunk = await chunk_storage_manager.update_chunk(
            db, chunk_id, request.content
        )
        
        if not updated_chunk:
            raise HTTPException(status_code=404, detail="Chunk not found")
        
        # Get document info
        result = await db.execute(
            select(Document).where(Document.id == updated_chunk.document_id)
        )
        document = result.scalar_one_or_none()
        
        response_data = ChunkResponse.model_validate(updated_chunk)
        if document:
            response_data.document_name = document.name
            response_data.document_type = document.type
        
        return response_data
        
    except VectorDatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/chunks/{chunk_id}")
async def delete_chunk(
    chunk_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a specific chunk"""
    try:
        # Get chunk to verify it exists and get vector_id
        chunk = await chunk_storage_manager.get_chunk_by_id(db, chunk_id)
        if not chunk:
            raise HTTPException(status_code=404, detail="Chunk not found")
        
        # Delete from vector database
        await chunk_storage_manager.vector_store.delete_documents([chunk.vector_id])
        
        # Delete from SQL database
        await db.delete(chunk)
        await db.commit()
        
        return {"message": "Chunk deleted successfully"}
        
    except VectorDatabaseError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chunks/stats", response_model=ChunkStatsResponse)
async def get_chunk_stats():
    """Get chunk storage statistics"""
    try:
        stats = await chunk_storage_manager.get_stats()
        return ChunkStatsResponse(**stats)
        
    except VectorDatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/{document_id}/chunks", response_model=List[ChunkResponse])
async def create_document_chunks(
    document_id: int,
    chunks: List[ChunkCreate],
    db: AsyncSession = Depends(get_db)
):
    """Create chunks for a document (for testing purposes)"""
    try:
        # Verify document exists
        result = await db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Convert to chunk data format
        chunk_data = []
        for chunk in chunks:
            chunk_data.append({
                "content": chunk.content,
                "start_char": chunk.start_char,
                "end_char": chunk.end_char,
                "token_count": chunk.token_count
            })
        
        # Store chunks
        created_chunks = await chunk_storage_manager.store_chunks(
            db, document_id, chunk_data
        )
        
        # Convert to response format
        response_chunks = []
        for chunk in created_chunks:
            chunk_data = ChunkResponse.model_validate(chunk)
            chunk_data.document_name = document.name
            chunk_data.document_type = document.type
            response_chunks.append(chunk_data)
        
        return response_chunks
        
    except VectorDatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{document_id}/chunks")
async def delete_document_chunks(
    document_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete all chunks for a document"""
    try:
        # Verify document exists
        result = await db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Delete chunks
        await chunk_storage_manager.delete_chunks(db, document_id)
        
        return {"message": f"All chunks for document {document_id} deleted successfully"}
        
    except VectorDatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))