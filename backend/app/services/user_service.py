"""
User service for handling user operations
"""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models.user import User
from ..core.auth import verify_password, get_password_hash
from ..schemas.auth import UserCreate


class UserService:
    """Service for user operations"""
    
    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
        """Get user by email"""
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
        """Get user by ID"""
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def create_user(db: AsyncSession, user_data: UserCreate) -> User:
        """Create a new user"""
        # Hash password
        hashed_password = get_password_hash(user_data.password)
        
        # Create user instance
        user = User(
            email=user_data.email,
            hashed_password=hashed_password
        )
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        return user
    
    @staticmethod
    async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password"""
        user = await UserService.get_user_by_email(db, email)
        
        if not user:
            return None
        
        if not verify_password(password, user.hashed_password):
            return None
        
        if not user.is_active:
            return None
        
        return user
    
    @staticmethod
    async def update_user_superuser_status(db: AsyncSession, user_id: int, is_superuser: bool) -> Optional[User]:
        """Update user's superuser status"""
        user = await UserService.get_user_by_id(db, user_id)
        if not user:
            return None
        
        user.is_superuser = is_superuser
        await db.commit()
        await db.refresh(user)
        
        return user
    
    @staticmethod
    async def get_all_users(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[User]:
        """Get all users with pagination"""
        result = await db.execute(select(User).offset(skip).limit(limit))
        return result.scalars().all()
    
    @staticmethod
    async def is_email_taken(db: AsyncSession, email: str) -> bool:
        """Check if email is already registered"""
        user = await UserService.get_user_by_email(db, email)
        return user is not None