"""
Application configuration settings
"""

from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict
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
    
    # Vector database settings
    chroma_host: str = Field(
        default="localhost",
        description="Chroma database host"
    )
    chroma_port: int = Field(
        default=8000,
        description="Chroma database port"
    )
    chroma_collection_name: str = Field(
        default="rag_documents",
        description="Chroma collection name"
    )
    chroma_persist_directory: str = Field(
        default="./storage/chroma",
        description="Chroma persistence directory"
    )
    
    # OpenAI settings
    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key"
    )
    openai_embedding_model: str = Field(
        default="text-embedding-ada-002",
        description="OpenAI embedding model"
    )
    openai_embedding_dimensions: int = Field(
        default=1536,
        description="OpenAI embedding dimensions"
    )
    
    # Chunking settings
    chunk_size: int = Field(
        default=1000,
        description="Text chunk size"
    )
    chunk_overlap: int = Field(
        default=200,
        description="Text chunk overlap"
    )
    
    model_config = ConfigDict(env_file=".env", case_sensitive=False)


settings = Settings()