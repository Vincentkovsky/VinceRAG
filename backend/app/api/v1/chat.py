"""
Chat endpoints for RAG query system
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from datetime import datetime
import json
import asyncio

from ...core.database import get_db
from ...core.deps import get_current_active_user
from ...models.user import User
from ...models.chat import ChatSession, ChatMessage
from ...services.rag_service import chat_manager, rag_service, RAGError
from sqlalchemy import select

router = APIRouter()


class ChatSessionCreate(BaseModel):
    """Schema for creating a chat session"""
    title: Optional[str] = Field(default=None, max_length=255)


class ChatSessionResponse(BaseModel):
    """Schema for chat session response"""
    id: int
    title: str
    created_at: str
    updated_at: Optional[str] = None
    message_count: int = 0
    title: str
    is_active: bool
    created_at: str
    updated_at: Optional[str] = None
    message_count: int = 0

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    """Schema for creating a message"""
    content: str = Field(..., min_length=1, max_length=5000)
    document_id: Optional[int] = None
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    enable_query_optimization: bool = Field(default=True)
    enable_result_ranking: bool = Field(default=True)
    use_cache: bool = Field(default=False)  # Disabled by default for chat sessions


class MessageResponse(BaseModel):
    """Schema for message response"""
    id: int
    session_id: int
    role: str
    content: str
    sources: Optional[List[Dict[str, Any]]] = None
    created_at: str

    class Config:
        from_attributes = True


class QueryResponse(BaseModel):
    """Schema for RAG query response"""
    session_id: int
    user_message_id: int
    assistant_message_id: int
    answer: str
    sources: List[Dict[str, Any]]
    confidence: float
    processing_time: float


class QueryRequest(BaseModel):
    """Schema for direct query request (without session)"""
    question: str = Field(..., min_length=1, max_length=5000)
    document_id: Optional[int] = None
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    enable_query_optimization: bool = Field(default=True)
    enable_result_ranking: bool = Field(default=True)
    use_cache: bool = Field(default=True)


class DirectQueryResponse(BaseModel):
    """Schema for direct query response"""
    answer: str
    sources: List[Dict[str, Any]]
    confidence: float
    processing_time: float
    retrieved_documents: int



@router.get("/sessions", response_model=List[ChatSessionResponse])
async def list_chat_sessions(
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_active_user),  # Temporarily disabled for testing
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100)
):
    """List all active chat sessions"""
    try:
        # Get sessions with message counts
        result = await db.execute(
            select(ChatSession)
            .where(ChatSession.is_active == True)
            .order_by(ChatSession.updated_at.desc().nulls_last(), ChatSession.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        sessions = result.scalars().all()
        
        # Get message counts for each session
        session_responses = []
        for session in sessions:
            message_count_result = await db.execute(
                select(ChatMessage.id).where(ChatMessage.session_id == session.id)
            )
            message_count = len(message_count_result.scalars().all())
            
            session_data = ChatSessionResponse.model_validate(session)
            session_data.message_count = message_count
            session_responses.append(session_data)
        
        return session_responses
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {e}")


@router.post("/sessions", response_model=ChatSessionResponse)
async def create_chat_session(
    session_data: ChatSessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new chat session"""
    try:
        session = await chat_manager.create_session(
            db, title=session_data.title
        )
        
        session_response = ChatSessionResponse.model_validate(session)
        session_response.message_count = 0
        return session_response
        
    except RAGError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_chat_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific chat session"""
    try:
        session = await chat_manager.get_session(db, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get message count
        message_count_result = await db.execute(
            select(ChatMessage.id).where(ChatMessage.session_id == session_id)
        )
        message_count = len(message_count_result.scalars().all())
        
        session_response = ChatSessionResponse.model_validate(session)
        session_response.message_count = message_count
        return session_response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get session: {e}")


@router.put("/sessions/{session_id}", response_model=ChatSessionResponse)
async def update_chat_session(
    session_id: int,
    session_data: ChatSessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a chat session"""
    try:
        if session_data.title:
            session = await chat_manager.update_session_title(
                db, session_id, session_data.title
            )
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
            
            session_response = ChatSessionResponse.model_validate(session)
            return session_response
        else:
            raise HTTPException(status_code=400, detail="Title is required for update")
        
    except HTTPException:
        raise
    except RAGError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a chat session"""
    try:
        success = await chat_manager.delete_session(db, session_id)
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {"message": "Session deleted successfully"}
        
    except HTTPException:
        raise
    except RAGError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/messages", response_model=QueryResponse)
async def send_message(
    session_id: int,
    message_data: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Send a message in a chat session and get RAG response"""
    try:
        response = await chat_manager.send_message(
            db=db,
            session_id=session_id,
            question=message_data.content,
            document_id=message_data.document_id,
            similarity_threshold=message_data.similarity_threshold,
            enable_query_optimization=message_data.enable_query_optimization,
            enable_result_ranking=message_data.enable_result_ranking,
            use_cache=message_data.use_cache
        )
        
        return QueryResponse(**response)
        
    except RAGError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/messages/stream")
async def send_message_stream(
    session_id: int,
    message_data: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Send a message and stream the RAG response"""
    try:
        async def generate_stream():
            async for chunk in chat_manager.stream_message(
                db=db,
                session_id=session_id,
                question=message_data.content,
                document_id=message_data.document_id,
                similarity_threshold=message_data.similarity_threshold
            ):
                yield f"data: {json.dumps(chunk)}\n\n"
            
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )
        
    except RAGError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    limit: int = Query(default=50, ge=1, le=100)
):
    """Get messages from a chat session"""
    try:
        # Verify session exists
        session = await chat_manager.get_session(db, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        messages = await chat_manager.get_session_messages(db, session_id, limit)
        
        return [MessageResponse.model_validate(msg) for msg in messages]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get messages: {e}")


@router.post("/query", response_model=DirectQueryResponse)
async def direct_query(
    query_data: QueryRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Direct RAG query without session management"""
    try:
        response = await rag_service.query(
            question=query_data.question,
            document_id=query_data.document_id,
            similarity_threshold=query_data.similarity_threshold,
            enable_query_optimization=query_data.enable_query_optimization,
            enable_result_ranking=query_data.enable_result_ranking,
            use_cache=query_data.use_cache
        )
        
        return DirectQueryResponse(**response)
        
    except RAGError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query/stream")
async def direct_query_stream(
    query_data: QueryRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Direct RAG query with streaming response"""
    try:
        async def generate_stream():
            async for chunk in rag_service.stream_query(
                question=query_data.question,
                document_id=query_data.document_id,
                similarity_threshold=query_data.similarity_threshold
            ):
                yield f"data: {json.dumps({'type': 'content_delta', 'delta': chunk})}\n\n"
            
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )
        
    except RAGError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suggestions")
async def get_query_suggestions(
    document_id: Optional[int] = Query(default=None),
    limit: int = Query(default=5, ge=1, le=10),
    current_user: User = Depends(get_current_active_user)
):
    """Get query suggestions"""
    try:
        suggestions = await rag_service.get_query_suggestions(
            document_id=document_id,
            limit=limit
        )
        
        return {"suggestions": suggestions}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get suggestions: {e}")


@router.post("/analyze")
async def analyze_query(
    query_data: QueryRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Analyze query complexity and provide insights"""
    try:
        analysis = await rag_service.analyze_query_complexity(query_data.question)
        
        return {"analysis": analysis}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze query: {e}")


@router.post("/cache/clear")
async def clear_query_cache(
    current_user: User = Depends(get_current_active_user)
):
    """Clear the query cache"""
    try:
        rag_service.clear_cache()
        return {"message": "Query cache cleared successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {e}")


@router.get("/cache/stats")
async def get_cache_stats(
    current_user: User = Depends(get_current_active_user)
):
    """Get query cache statistics"""
    try:
        stats = rag_service.get_cache_stats()
        return {"cache_stats": stats}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cache stats: {e}")


@router.post("/no-results-help")
async def get_no_results_help(
    query_data: QueryRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Get help when no results are found for a query"""
    try:
        help_response = await rag_service.handle_no_results(
            query_data.question,
            query_data.document_id
        )
        
        return help_response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get help: {e}")