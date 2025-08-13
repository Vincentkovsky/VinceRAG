"""
Comprehensive health check system for all system components
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum
import logging
import redis.asyncio as redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .database import get_db_session
from .metrics import metrics_collector

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ComponentHealth:
    """Individual component health information"""
    
    def __init__(self, name: str, status: HealthStatus, message: str = "", 
                 response_time: Optional[float] = None, details: Optional[Dict] = None):
        self.name = name
        self.status = status
        self.message = message
        self.response_time = response_time
        self.details = details or {}
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "response_time": self.response_time,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }


class HealthChecker:
    """Comprehensive health checking system"""
    
    def __init__(self):
        self._health_cache = {}
        self._cache_ttl = timedelta(seconds=30)
        self._last_check = {}
    
    async def check_all_components(self) -> Dict[str, Any]:
        """Check health of all system components"""
        components = []
        overall_status = HealthStatus.HEALTHY
        
        # Check each component
        checks = [
            self.check_database(),
            self.check_redis(),
            self.check_vector_database(),
            self.check_file_system(),
            self.check_external_services(),
            self.check_system_resources()
        ]
        
        results = await asyncio.gather(*checks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Health check failed: {result}")
                components.append(ComponentHealth(
                    name="unknown",
                    status=HealthStatus.UNHEALTHY,
                    message=str(result)
                ))
                overall_status = HealthStatus.UNHEALTHY
            else:
                components.append(result)
                if result.status == HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.UNHEALTHY
                elif result.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED
        
        return {
            "status": overall_status.value,
            "timestamp": datetime.now().isoformat(),
            "components": [comp.to_dict() for comp in components],
            "summary": {
                "total_components": len(components),
                "healthy": sum(1 for c in components if c.status == HealthStatus.HEALTHY),
                "degraded": sum(1 for c in components if c.status == HealthStatus.DEGRADED),
                "unhealthy": sum(1 for c in components if c.status == HealthStatus.UNHEALTHY)
            }
        }
    
    async def check_database(self) -> ComponentHealth:
        """Check database connectivity and performance"""
        start_time = time.time()
        
        try:
            session = await get_db_session()
            async with session:
                # Simple query to test connectivity
                result = await session.execute(text("SELECT 1"))
                await result.fetchone()
                
                # Check connection pool status
                pool = session.get_bind().pool
                pool_status = {
                    "size": pool.size(),
                    "checked_in": pool.checkedin(),
                    "checked_out": pool.checkedout(),
                    "overflow": pool.overflow(),
                    "invalid": pool.invalid()
                }
                
                response_time = time.time() - start_time
                
                # Determine status based on response time and pool usage
                if response_time > 5.0:
                    status = HealthStatus.DEGRADED
                    message = f"Database responding slowly ({response_time:.2f}s)"
                elif pool.checkedout() / pool.size() > 0.8:
                    status = HealthStatus.DEGRADED
                    message = "Database connection pool usage high"
                else:
                    status = HealthStatus.HEALTHY
                    message = "Database operational"
                
                return ComponentHealth(
                    name="database",
                    status=status,
                    message=message,
                    response_time=response_time,
                    details=pool_status
                )
                
        except Exception as e:
            return ComponentHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database connection failed: {str(e)}",
                response_time=time.time() - start_time
            )
    
    async def check_redis(self) -> ComponentHealth:
        """Check Redis connectivity and performance"""
        start_time = time.time()
        
        try:
            redis_client = redis.from_url(settings.redis_url)
            
            # Test basic operations
            await redis_client.ping()
            test_key = "health_check_test"
            await redis_client.set(test_key, "test_value", ex=60)
            value = await redis_client.get(test_key)
            await redis_client.delete(test_key)
            
            # Get Redis info
            info = await redis_client.info()
            
            response_time = time.time() - start_time
            
            # Check memory usage
            memory_usage = info.get('used_memory', 0) / info.get('maxmemory', 1) if info.get('maxmemory') else 0
            
            if response_time > 2.0:
                status = HealthStatus.DEGRADED
                message = f"Redis responding slowly ({response_time:.2f}s)"
            elif memory_usage > 0.9:
                status = HealthStatus.DEGRADED
                message = f"Redis memory usage high ({memory_usage:.1%})"
            else:
                status = HealthStatus.HEALTHY
                message = "Redis operational"
            
            await redis_client.close()
            
            return ComponentHealth(
                name="redis",
                status=status,
                message=message,
                response_time=response_time,
                details={
                    "memory_usage": memory_usage,
                    "connected_clients": info.get('connected_clients', 0),
                    "version": info.get('redis_version', 'unknown')
                }
            )
            
        except Exception as e:
            return ComponentHealth(
                name="redis",
                status=HealthStatus.UNHEALTHY,
                message=f"Redis connection failed: {str(e)}",
                response_time=time.time() - start_time
            )    

    async def check_vector_database(self) -> ComponentHealth:
        """Check vector database connectivity"""
        start_time = time.time()
        
        try:
            # Import here to avoid circular imports
            from ..services.vector_service import vector_service
            
            # Test vector database connection
            collection_info = await vector_service.get_collection_info()
            
            response_time = time.time() - start_time
            
            if response_time > 3.0:
                status = HealthStatus.DEGRADED
                message = f"Vector database responding slowly ({response_time:.2f}s)"
            else:
                status = HealthStatus.HEALTHY
                message = "Vector database operational"
            
            return ComponentHealth(
                name="vector_database",
                status=status,
                message=message,
                response_time=response_time,
                details=collection_info
            )
            
        except Exception as e:
            return ComponentHealth(
                name="vector_database",
                status=HealthStatus.UNHEALTHY,
                message=f"Vector database check failed: {str(e)}",
                response_time=time.time() - start_time
            )
    
    async def check_file_system(self) -> ComponentHealth:
        """Check file system health and storage"""
        start_time = time.time()
        
        try:
            import os
            import shutil
            from pathlib import Path
            
            # Check upload directory
            upload_dir = Path(settings.upload_dir)
            upload_dir.mkdir(parents=True, exist_ok=True)
            
            # Check disk space
            disk_usage = shutil.disk_usage(upload_dir)
            free_space_gb = disk_usage.free / (1024**3)
            total_space_gb = disk_usage.total / (1024**3)
            usage_percent = (disk_usage.used / disk_usage.total) * 100
            
            # Test write permissions
            test_file = upload_dir / "health_check_test.txt"
            test_file.write_text("test")
            test_file.unlink()
            
            response_time = time.time() - start_time
            
            if free_space_gb < 1.0:  # Less than 1GB free
                status = HealthStatus.UNHEALTHY
                message = f"Low disk space: {free_space_gb:.1f}GB free"
            elif usage_percent > 90:
                status = HealthStatus.DEGRADED
                message = f"High disk usage: {usage_percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = "File system operational"
            
            return ComponentHealth(
                name="file_system",
                status=status,
                message=message,
                response_time=response_time,
                details={
                    "free_space_gb": round(free_space_gb, 2),
                    "total_space_gb": round(total_space_gb, 2),
                    "usage_percent": round(usage_percent, 1),
                    "upload_dir": str(upload_dir)
                }
            )
            
        except Exception as e:
            return ComponentHealth(
                name="file_system",
                status=HealthStatus.UNHEALTHY,
                message=f"File system check failed: {str(e)}",
                response_time=time.time() - start_time
            )
    
    async def check_external_services(self) -> ComponentHealth:
        """Check external service dependencies"""
        start_time = time.time()
        
        try:
            import openai
            
            # Test OpenAI API if configured
            if settings.openai_api_key:
                client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
                
                # Simple API test
                models = await client.models.list()
                
                response_time = time.time() - start_time
                
                if response_time > 5.0:
                    status = HealthStatus.DEGRADED
                    message = f"OpenAI API responding slowly ({response_time:.2f}s)"
                else:
                    status = HealthStatus.HEALTHY
                    message = "External services operational"
                
                return ComponentHealth(
                    name="external_services",
                    status=status,
                    message=message,
                    response_time=response_time,
                    details={
                        "openai_available": True,
                        "models_count": len(models.data) if models else 0
                    }
                )
            else:
                return ComponentHealth(
                    name="external_services",
                    status=HealthStatus.HEALTHY,
                    message="No external services configured",
                    response_time=time.time() - start_time
                )
                
        except Exception as e:
            return ComponentHealth(
                name="external_services",
                status=HealthStatus.DEGRADED,
                message=f"External service check failed: {str(e)}",
                response_time=time.time() - start_time
            )
    
    async def check_system_resources(self) -> ComponentHealth:
        """Check system resource usage"""
        start_time = time.time()
        
        try:
            import psutil
            
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            response_time = time.time() - start_time
            
            # Determine status based on resource usage
            if cpu_percent > 90 or memory.percent > 90 or disk.percent > 95:
                status = HealthStatus.UNHEALTHY
                message = "Critical resource usage"
            elif cpu_percent > 80 or memory.percent > 80 or disk.percent > 90:
                status = HealthStatus.DEGRADED
                message = "High resource usage"
            else:
                status = HealthStatus.HEALTHY
                message = "System resources normal"
            
            return ComponentHealth(
                name="system_resources",
                status=status,
                message=message,
                response_time=response_time,
                details={
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "disk_percent": disk.percent,
                    "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
                }
            )
            
        except Exception as e:
            return ComponentHealth(
                name="system_resources",
                status=HealthStatus.UNHEALTHY,
                message=f"System resource check failed: {str(e)}",
                response_time=time.time() - start_time
            )
    
    async def check_component(self, component_name: str) -> ComponentHealth:
        """Check a specific component"""
        check_methods = {
            "database": self.check_database,
            "redis": self.check_redis,
            "vector_database": self.check_vector_database,
            "file_system": self.check_file_system,
            "external_services": self.check_external_services,
            "system_resources": self.check_system_resources
        }
        
        if component_name not in check_methods:
            return ComponentHealth(
                name=component_name,
                status=HealthStatus.UNHEALTHY,
                message=f"Unknown component: {component_name}"
            )
        
        return await check_methods[component_name]()
    
    def get_cached_health(self, component_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get cached health check results"""
        if component_name:
            return self._health_cache.get(component_name)
        return self._health_cache
    
    async def run_health_checks_periodically(self):
        """Run health checks periodically and cache results"""
        while True:
            try:
                health_data = await self.check_all_components()
                self._health_cache["all"] = health_data
                self._last_check["all"] = datetime.now()
                
                # Cache individual component results
                for component in health_data["components"]:
                    self._health_cache[component["name"]] = component
                    self._last_check[component["name"]] = datetime.now()
                
                await asyncio.sleep(settings.health_check_interval)
                
            except Exception as e:
                logger.error(f"Error in periodic health checks: {e}")
                await asyncio.sleep(60)  # Wait longer on error


# Global health checker instance
health_checker = HealthChecker()