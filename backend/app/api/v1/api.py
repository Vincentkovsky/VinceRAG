"""
API v1 router
"""

from fastapi import APIRouter

from .auth import router as auth_router
from .documents import router as documents_router
from .chat import router as chat_router
from .admin import router as admin_router
from .chunks import router as chunks_router

api_router = APIRouter()

# Include all routers
api_router.include_router(auth_router, prefix="/auth", tags=["authentication"])
api_router.include_router(documents_router, prefix="/documents", tags=["documents"])
api_router.include_router(chat_router, prefix="/chat", tags=["chat"])
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
api_router.include_router(chunks_router, tags=["chunks"])