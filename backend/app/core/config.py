"""
Application configuration settings with hot reloading support
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict, validator
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading

logger = logging.getLogger(__name__)


class ConfigFileHandler(FileSystemEventHandler):
    """Handler for configuration file changes"""
    
    def __init__(self, config_instance):
        self.config_instance = config_instance
        
    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith('.env'):
            logger.info(f"Configuration file changed: {event.src_path}")
            self.config_instance.reload_config()


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
    
    # Logging settings
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format"
    )
    log_file: Optional[str] = Field(default=None, description="Log file path")
    structured_logging: bool = Field(default=True, description="Enable structured JSON logging")
    
    # Monitoring settings
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    metrics_port: int = Field(default=8001, description="Metrics server port")
    health_check_interval: int = Field(default=30, description="Health check interval in seconds")
    
    # Performance settings
    request_timeout: int = Field(default=30, description="Request timeout in seconds")
    max_concurrent_requests: int = Field(default=100, description="Maximum concurrent requests")
    
    # Hot reload settings
    enable_hot_reload: bool = Field(default=True, description="Enable configuration hot reloading")
    config_watch_paths: List[str] = Field(
        default=[".env", "config/"],
        description="Paths to watch for configuration changes"
    )
    
    model_config = ConfigDict(env_file=".env", case_sensitive=False)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._config_observer = None
        self._reload_callbacks = []
        self._last_reload = datetime.now()
        self._lock = threading.Lock()
        
        if self.enable_hot_reload:
            self._setup_hot_reload()
    
    def _setup_hot_reload(self):
        """Setup file system watcher for configuration hot reloading"""
        try:
            self._config_observer = Observer()
            handler = ConfigFileHandler(self)
            
            # Watch .env file
            env_path = Path(".env")
            if env_path.exists():
                self._config_observer.schedule(
                    handler, 
                    str(env_path.parent), 
                    recursive=False
                )
            
            # Watch config directory if it exists
            config_dir = Path("config")
            if config_dir.exists():
                self._config_observer.schedule(
                    handler,
                    str(config_dir),
                    recursive=True
                )
            
            self._config_observer.start()
            logger.info("Configuration hot reloading enabled")
            
        except Exception as e:
            logger.warning(f"Failed to setup configuration hot reloading: {e}")
    
    def reload_config(self):
        """Reload configuration from environment and files"""
        with self._lock:
            try:
                # Re-read environment variables
                old_values = self.model_dump()
                
                # Create new instance with current environment
                new_settings = Settings(_env_file=".env")
                
                # Update current instance
                for key, value in new_settings.model_dump().items():
                    if hasattr(self, key) and getattr(self, key) != value:
                        setattr(self, key, value)
                        logger.info(f"Configuration updated: {key} = {value}")
                
                self._last_reload = datetime.now()
                
                # Notify callbacks
                for callback in self._reload_callbacks:
                    try:
                        callback(old_values, self.model_dump())
                    except Exception as e:
                        logger.error(f"Error in reload callback: {e}")
                
                logger.info("Configuration reloaded successfully")
                
            except Exception as e:
                logger.error(f"Failed to reload configuration: {e}")
    
    def add_reload_callback(self, callback):
        """Add callback to be called when configuration is reloaded"""
        self._reload_callbacks.append(callback)
    
    def get_config_info(self) -> Dict[str, Any]:
        """Get configuration information for monitoring"""
        return {
            "last_reload": self._last_reload.isoformat(),
            "hot_reload_enabled": self.enable_hot_reload,
            "config_values": {
                key: "***" if "key" in key.lower() or "secret" in key.lower() or "password" in key.lower()
                else value
                for key, value in self.model_dump().items()
            }
        }
    
    def cleanup(self):
        """Cleanup resources"""
        if self._config_observer:
            self._config_observer.stop()
            self._config_observer.join()


# Global settings instance
settings = Settings()