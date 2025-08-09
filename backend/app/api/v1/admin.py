"""
Admin endpoints
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.deps import get_current_superuser
from ...models.user import User

router = APIRouter()


@router.get("/users")
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """List all users (admin only)"""
    return {"message": "Admin users endpoint - coming soon"}


@router.get("/stats")
async def get_system_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """Get system statistics (admin only)"""
    return {"message": "Admin stats endpoint - coming soon"}


@router.post("/users/{user_id}/activate")
async def activate_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """Activate a user (admin only)"""
    return {"message": f"Activate user {user_id} - coming soon"}


@router.post("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """Deactivate a user (admin only)"""
    return {"message": f"Deactivate user {user_id} - coming soon"}