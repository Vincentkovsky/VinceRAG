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