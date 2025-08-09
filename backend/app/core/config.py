"""
Application configuration settings
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""
    
    # Database settings
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:password@localhost:5432/rag_system",
        description="Database URL"
    )
    database_pool_size: int = Field(default=10, description="Database connection pool size")
    database_max_overflow: int = Field(default=20, description="Database max overflow connections")
    
    # Redis settings
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis URL"
    )
    
    @property
    def REDIS_URL(self) -> str:
        """Redis URL for Celery compatibility"""
        return self.redis_url
    
    # JWT settings
    secret_key: str = Field(
        default="your-secret-key-change-in-production",
        description="JWT secret key"
    )
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(
        default=30, 
        description="Access token expiration time in minutes"
    )
    
    # API settings
    api_v1_str: str = Field(default="/api/v1", description="API v1 prefix")
    project_name: str = Field(default="RAG System", description="Project name")
    debug: bool = Field(default=False, description="Debug mode")
    
    # CORS settings
    backend_cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        description="Allowed CORS origins"
    )
    
    # File upload settings
    max_file_size: int = Field(
        default=50 * 1024 * 1024,  # 50MB
        description="Maximum file size in bytes"
    )
    upload_dir: str = Field(
        default="./uploads",
        description="Upload directory"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()