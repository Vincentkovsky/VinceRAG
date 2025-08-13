"""
FastAPI middleware with comprehensive logging and metrics
"""

import time
import uuid
import logging
from typing import Callable
from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from .config import settings
from .logging import LoggingContext, get_logger
from .metrics import metrics_collector

logger = get_logger("middleware")


class LoggingMiddleware(BaseHTTPMiddleware):
    """Enhanced request logging middleware with metrics collection"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Extract user ID from request if available
        user_id = None
        if hasattr(request.state, 'user_id'):
            user_id = request.state.user_id
        
        # Set up logging context
        with LoggingContext(request_id=request_id, user_id=user_id):
            # Increment active requests
            metrics_collector.increment_active_requests()
            
            try:
                # Log request start
                logger.info(
                    f"Request started: {request.method} {request.url.path}",
                    extra={
                        "method": request.method,
                        "path": request.url.path,
                        "query_params": str(request.query_params),
                        "client_ip": request.client.host if request.client else None,
                        "user_agent": request.headers.get("user-agent")
                    }
                )
                
                # Process request
                response = await call_next(request)
                
                # Calculate processing time
                process_time = time.time() - start_time
                
                # Record metrics
                metrics_collector.record_request(
                    method=request.method,
                    endpoint=request.url.path,
                    status_code=response.status_code,
                    duration=process_time
                )
                
                # Log response
                log_level = logging.WARNING if response.status_code >= 400 else logging.INFO
                logger.log(
                    log_level,
                    f"Request completed: {response.status_code}",
                    extra={
                        "status_code": response.status_code,
                        "duration": process_time,
                        "response_size": response.headers.get("content-length")
                    }
                )
                
                # Add headers
                response.headers["X-Request-ID"] = request_id
                response.headers["X-Process-Time"] = f"{process_time:.4f}"
                
                return response
                
            except Exception as e:
                process_time = time.time() - start_time
                
                # Record error metrics
                metrics_collector.record_request(
                    method=request.method,
                    endpoint=request.url.path,
                    status_code=500,
                    duration=process_time
                )
                
                # Log error
                logger.error(
                    f"Request failed: {str(e)}",
                    exc_info=True,
                    extra={
                        "duration": process_time,
                        "error_type": type(e).__name__
                    }
                )
                
                raise
                
            finally:
                # Decrement active requests
                metrics_collector.decrement_active_requests()


def setup_cors(app):
    """Setup CORS middleware"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.backend_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def setup_security_headers(app):
    """Setup security headers middleware"""
    
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        if not settings.debug:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response