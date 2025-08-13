"""
Admin API endpoints for system configuration and monitoring
"""

from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ...core.config import settings
from ...core.health import health_checker, HealthStatus
from ...core.metrics import metrics_collector
from ...core.logging import get_logger
from ...core.database import get_db
from ...core.deps import get_current_superuser
from ...services.user_service import UserService
from ...schemas.auth import User as UserSchema
from ...models.user import User
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger("admin")
router = APIRouter()


class ConfigUpdateRequest(BaseModel):
    """Request model for configuration updates"""
    key: str
    value: Any


class SystemStatusResponse(BaseModel):
    """System status response model"""
    status: str
    uptime_seconds: float
    components: List[Dict[str, Any]]
    metrics: Dict[str, Any]


@router.get("/health")
async def health_check():
    """Basic health check endpoint"""
    try:
        health_data = await health_checker.check_all_components()
        
        status_code = 200
        if health_data["status"] == HealthStatus.DEGRADED.value:
            status_code = 200  # Still OK, but with warnings
        elif health_data["status"] == HealthStatus.UNHEALTHY.value:
            status_code = 503  # Service unavailable
        
        return JSONResponse(
            status_code=status_code,
            content=health_data
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "message": "Health check system failure",
                "error": str(e)
            }
        )


@router.get("/health/{component}")
async def health_check_component(component: str):
    """Check health of a specific component"""
    try:
        component_health = await health_checker.check_component(component)
        
        status_code = 200
        if component_health.status == HealthStatus.DEGRADED:
            status_code = 200
        elif component_health.status == HealthStatus.UNHEALTHY:
            status_code = 503
        
        return JSONResponse(
            status_code=status_code,
            content=component_health.to_dict()
        )
        
    except Exception as e:
        logger.error(f"Component health check failed for {component}: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "name": component,
                "status": "unhealthy",
                "message": f"Health check failed: {str(e)}"
            }
        )


@router.get("/metrics")
async def get_metrics():
    """Get current system metrics"""
    try:
        metrics = metrics_collector.get_current_metrics()
        return metrics
        
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics")


@router.get("/metrics/history")
async def get_metrics_history(hours: int = Query(default=1, ge=1, le=24)):
    """Get metrics history for specified hours"""
    try:
        history = metrics_collector.get_metrics_history(hours=hours)
        return history
        
    except Exception as e:
        logger.error(f"Failed to get metrics history: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics history")


@router.get("/config")
async def get_configuration():
    """Get current system configuration"""
    try:
        config_info = settings.get_config_info()
        return config_info
        
    except Exception as e:
        logger.error(f"Failed to get configuration: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve configuration")


@router.post("/config/reload")
async def reload_configuration():
    """Reload system configuration"""
    try:
        old_config = settings.model_dump()
        settings.reload_config()
        new_config = settings.model_dump()
        
        # Find changed values
        changes = {}
        for key, new_value in new_config.items():
            old_value = old_config.get(key)
            if old_value != new_value:
                changes[key] = {
                    "old": old_value,
                    "new": new_value
                }
        
        logger.info(f"Configuration reloaded with {len(changes)} changes")
        
        return {
            "message": "Configuration reloaded successfully",
            "changes": changes,
            "reload_time": settings._last_reload.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to reload configuration: {e}")
        raise HTTPException(status_code=500, detail="Failed to reload configuration")


@router.get("/status")
async def get_system_status():
    """Get comprehensive system status"""
    try:
        # Get health data
        health_data = await health_checker.check_all_components()
        
        # Get metrics
        metrics = metrics_collector.get_current_metrics()
        
        # Combine into system status
        status_data = {
            "status": health_data["status"],
            "timestamp": health_data["timestamp"],
            "uptime_seconds": metrics.get("uptime_seconds", 0),
            "components": health_data["components"],
            "metrics": {
                "system": metrics.get("system", {}),
                "application": metrics.get("application", {}),
                "error_breakdown": metrics.get("error_breakdown", {})
            },
            "summary": health_data["summary"]
        }
        
        return status_data
        
    except Exception as e:
        logger.error(f"Failed to get system status: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve system status")


@router.get("/logs")
async def get_recent_logs(
    level: Optional[str] = Query(default=None, description="Log level filter"),
    limit: int = Query(default=100, ge=1, le=1000, description="Number of log entries"),
    component: Optional[str] = Query(default=None, description="Component filter")
):
    """Get recent log entries (if file logging is enabled)"""
    try:
        if not settings.log_file:
            raise HTTPException(
                status_code=404, 
                detail="File logging is not enabled"
            )
        
        import json
        from pathlib import Path
        
        log_file = Path(settings.log_file)
        if not log_file.exists():
            return {"logs": [], "message": "Log file not found"}
        
        logs = []
        with open(log_file, 'r') as f:
            lines = f.readlines()
            
            # Get last N lines
            recent_lines = lines[-limit:] if len(lines) > limit else lines
            
            for line in recent_lines:
                try:
                    log_entry = json.loads(line.strip())
                    
                    # Apply filters
                    if level and log_entry.get("level") != level.upper():
                        continue
                    
                    if component and not log_entry.get("logger", "").startswith(f"app.{component}"):
                        continue
                    
                    logs.append(log_entry)
                    
                except json.JSONDecodeError:
                    # Skip non-JSON lines
                    continue
        
        return {
            "logs": logs,
            "total": len(logs),
            "filters": {
                "level": level,
                "component": component,
                "limit": limit
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve logs")


@router.post("/maintenance/gc")
async def trigger_garbage_collection():
    """Trigger garbage collection (for debugging)"""
    try:
        import gc
        
        before_count = len(gc.get_objects())
        collected = gc.collect()
        after_count = len(gc.get_objects())
        
        logger.info(f"Garbage collection completed: {collected} objects collected")
        
        return {
            "message": "Garbage collection completed",
            "objects_before": before_count,
            "objects_after": after_count,
            "objects_collected": collected
        }
        
    except Exception as e:
        logger.error(f"Garbage collection failed: {e}")
        raise HTTPException(status_code=500, detail="Garbage collection failed")


@router.get("/info")
async def get_system_info():
    """Get system information"""
    try:
        import sys
        import platform
        from datetime import datetime
        
        info = {
            "application": {
                "name": settings.project_name,
                "version": "1.0.0",
                "debug_mode": settings.debug,
                "environment": "development" if settings.debug else "production"
            },
            "system": {
                "platform": platform.platform(),
                "python_version": sys.version,
                "architecture": platform.architecture()[0],
                "processor": platform.processor(),
                "hostname": platform.node()
            },
            "runtime": {
                "uptime_seconds": metrics_collector.get_current_metrics().get("uptime_seconds", 0),
                "current_time": datetime.now().isoformat(),
                "timezone": str(datetime.now().astimezone().tzinfo)
            }
        }
        
        return info
        
    except Exception as e:
        logger.error(f"Failed to get system info: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve system information")


# User Management Endpoints
class UserUpdateRequest(BaseModel):
    """Request model for user updates"""
    is_superuser: bool


class AIModelConfig(BaseModel):
    """AI Model configuration with separate providers for embedding and chat"""
    embedding_provider: str
    chat_provider: str
    openai_api_key: Optional[str] = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_embedding_model: str = "text-embedding-ada-002"
    openai_embedding_dimensions: int = 1536
    openai_chat_model: str = "gpt-3.5-turbo"
    qwen_api_key: Optional[str] = None
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    qwen_embedding_model: str = "text-embedding-v2"
    qwen_embedding_dimensions: int = 1536
    qwen_chat_model: str = "qwen-max-latest"
    custom_api_key: Optional[str] = None
    custom_base_url: str = ""
    custom_embedding_model: str = ""
    custom_embedding_dimensions: int = 1536
    custom_chat_model: str = ""


@router.get("/users", response_model=List[UserSchema])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """Get all users (superuser only)"""
    try:
        users = await UserService.get_all_users(db, skip=skip, limit=limit)
        return users
    except Exception as e:
        logger.error(f"Failed to list users: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve users")


@router.put("/users/{user_id}", response_model=UserSchema)
async def update_user(
    user_id: int,
    update_data: UserUpdateRequest,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """Update user (superuser only)"""
    try:
        # Prevent user from removing their own superuser status
        if user_id == current_user.id and not update_data.is_superuser:
            raise HTTPException(
                status_code=400, 
                detail="Cannot remove superuser status from yourself"
            )
        
        user = await UserService.update_user_superuser_status(
            db, user_id, update_data.is_superuser
        )
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update user")


# AI Model Configuration Endpoints

@router.get("/models/config", response_model=AIModelConfig)
async def get_model_config(
    current_user: User = Depends(get_current_superuser)
):
    """Get current AI model configuration"""
    try:
        return AIModelConfig(
            embedding_provider=settings.embedding_provider,
            chat_provider=settings.chat_provider,
            openai_api_key="***" if settings.openai_api_key else None,
            openai_base_url=settings.openai_base_url,
            openai_embedding_model=settings.openai_embedding_model,
            openai_embedding_dimensions=settings.openai_embedding_dimensions,
            openai_chat_model=settings.openai_chat_model,
            qwen_api_key="***" if settings.qwen_api_key else None,
            qwen_base_url=settings.qwen_base_url,
            qwen_embedding_model=settings.qwen_embedding_model,
            qwen_embedding_dimensions=settings.qwen_embedding_dimensions,
            qwen_chat_model=settings.qwen_chat_model,
            custom_api_key="***" if settings.custom_api_key else None,
            custom_base_url=settings.custom_base_url,
            custom_embedding_model=settings.custom_embedding_model,
            custom_embedding_dimensions=settings.custom_embedding_dimensions,
            custom_chat_model=settings.custom_chat_model
        )
    except Exception as e:
        logger.error(f"Failed to get model config: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve model configuration")


@router.put("/models/config")
async def update_model_config(
    config: AIModelConfig,
    current_user: User = Depends(get_current_superuser)
):
    """Update AI model configuration"""
    try:
        # Update settings
        settings.embedding_provider = config.embedding_provider
        settings.chat_provider = config.chat_provider
        
        # OpenAI settings
        if config.openai_api_key and config.openai_api_key != "***":
            settings.openai_api_key = config.openai_api_key
        settings.openai_base_url = config.openai_base_url
        settings.openai_embedding_model = config.openai_embedding_model
        settings.openai_embedding_dimensions = config.openai_embedding_dimensions
        settings.openai_chat_model = config.openai_chat_model
        
        # Qwen settings
        if config.qwen_api_key and config.qwen_api_key != "***":
            settings.qwen_api_key = config.qwen_api_key
        settings.qwen_base_url = config.qwen_base_url
        settings.qwen_embedding_model = config.qwen_embedding_model
        settings.qwen_embedding_dimensions = config.qwen_embedding_dimensions
        settings.qwen_chat_model = config.qwen_chat_model
        
        # Custom settings
        if config.custom_api_key and config.custom_api_key != "***":
            settings.custom_api_key = config.custom_api_key
        settings.custom_base_url = config.custom_base_url
        settings.custom_embedding_model = config.custom_embedding_model
        settings.custom_embedding_dimensions = config.custom_embedding_dimensions
        settings.custom_chat_model = config.custom_chat_model
        
        logger.info(f"Model configuration updated by user {current_user.email}")
        
        return {"message": "Model configuration updated successfully"}
        
    except Exception as e:
        logger.error(f"Failed to update model config: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update model configuration")


@router.post("/models/test")
async def test_model_connection(
    config: AIModelConfig,
    current_user: User = Depends(get_current_superuser)
):
    """Test AI model connection with given configuration"""
    try:
        from openai import AsyncOpenAI
        
        # Test embedding provider
        embedding_api_key = None
        embedding_base_url = None
        embedding_model = None
        
        if config.embedding_provider == "openai":
            embedding_api_key = config.openai_api_key
            embedding_base_url = config.openai_base_url
            embedding_model = config.openai_embedding_model
        elif config.embedding_provider == "qwen":
            embedding_api_key = config.qwen_api_key
            embedding_base_url = config.qwen_base_url
            embedding_model = config.qwen_embedding_model
        elif config.embedding_provider == "custom":
            embedding_api_key = config.custom_api_key
            embedding_base_url = config.custom_base_url
            embedding_model = config.custom_embedding_model
        
        if not embedding_api_key:
            return {"success": False, "error": f"API key is required for embedding provider: {config.embedding_provider}"}
        
        if not embedding_model:
            return {"success": False, "error": f"Embedding model is required for provider: {config.embedding_provider}"}
        
        # Test embedding connection
        embedding_client = AsyncOpenAI(api_key=embedding_api_key, base_url=embedding_base_url)
        
        embedding_response = await embedding_client.embeddings.create(
            model=embedding_model,
            input=["test embedding"]
        )
        
        embedding_dimensions = len(embedding_response.data[0].embedding)
        
        # Test chat provider (if different from embedding)
        chat_test_result = ""
        if config.chat_provider != config.embedding_provider:
            chat_api_key = None
            chat_base_url = None
            chat_model = None
            
            if config.chat_provider == "openai":
                chat_api_key = config.openai_api_key
                chat_base_url = config.openai_base_url
                chat_model = config.openai_chat_model
            elif config.chat_provider == "qwen":
                chat_api_key = config.qwen_api_key
                chat_base_url = config.qwen_base_url
                chat_model = config.qwen_chat_model
            elif config.chat_provider == "custom":
                chat_api_key = config.custom_api_key
                chat_base_url = config.custom_base_url
                chat_model = config.custom_chat_model
            
            if not chat_api_key:
                return {"success": False, "error": f"API key is required for chat provider: {config.chat_provider}"}
            
            if not chat_model:
                return {"success": False, "error": f"Chat model is required for provider: {config.chat_provider}"}
            
            # Test chat connection
            chat_client = AsyncOpenAI(api_key=chat_api_key, base_url=chat_base_url)
            
            try:
                chat_response = await chat_client.chat.completions.create(
                    model=chat_model,
                    messages=[{"role": "user", "content": "Hello"}],
                    max_tokens=5
                )
                chat_test_result = f" Chat provider ({config.chat_provider}) also tested successfully."
            except Exception as chat_error:
                return {"success": False, "error": f"Chat provider test failed: {str(chat_error)}"}
        
        success_message = f"Embedding provider ({config.embedding_provider}) tested successfully."
        if chat_test_result:
            success_message += chat_test_result
        elif config.chat_provider == config.embedding_provider:
            success_message += f" Using same provider for chat ({config.chat_provider})."
        
        return {
            "success": True,
            "message": success_message,
            "embedding_dimensions": embedding_dimensions
        }
        
    except Exception as e:
        logger.error(f"Model connection test failed: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }