"""
Chat endpoints
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.deps import get_current_active_user
from ...models.user import User

router = APIRouter()


@router.get("/sessions")
async def list_chat_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all chat sessions"""
    return {"message": "Chat sessions endpoint - coming soon"}


@router.post("/sessions")
async def create_chat_session(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new chat session"""
    return {"message": "Create chat session endpoint - coming soon"}


@router.get("/sessions/{session_id}")
async def get_chat_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific chat session"""
    return {"message": f"Get chat session {session_id} - coming soon"}


@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Send a message in a chat session"""
    return {"message": f"Send message to session {session_id} - coming soon"}


@router.get("/sessions/{session_id}/messages")
async def get_messages(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get messages from a chat session"""
    return {"message": f"Get messages from session {session_id} - coming soon"}