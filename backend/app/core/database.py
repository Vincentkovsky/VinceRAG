"""
Database connection and session management
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
from typing import AsyncGenerator
import logging

from .config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base class for all database models"""
    pass


# Create async engine with connection pooling (lazy initialization)
engine = None
AsyncSessionLocal = None

def get_engine():
    """Get or create database engine"""
    global engine
    if engine is None:
        engine = create_async_engine(
            settings.database_url,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_pre_ping=True,
            echo=settings.debug,
            poolclass=NullPool if "sqlite" in settings.database_url else None
        )
    return engine

def get_session_factory():
    """Get or create session factory"""
    global AsyncSessionLocal
    if AsyncSessionLocal is None:
        AsyncSessionLocal = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False
        )
    return AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database tables"""
    engine = get_engine()
    async with engine.begin() as conn:
        # Import all models to ensure they are registered
        from ..models import document, chat, user  # noqa
        
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")


async def get_db_session() -> AsyncSession:
    """Get a database session for health checks and other utilities"""
    session_factory = get_session_factory()
    return session_factory()


async def close_db():
    """Close database connections"""
    engine = get_engine()
    await engine.dispose()
    logger.info("Database connections closed")