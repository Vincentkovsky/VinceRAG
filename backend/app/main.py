"""
FastAPI main application with comprehensive configuration and monitoring
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .core.config import settings
from .core.database import init_db, close_db
from .core.logging import setup_logging, get_logger
from .core.middleware import LoggingMiddleware, setup_cors, setup_security_headers
from .core.health import health_checker
from .api.v1.api import api_router

# Setup logging system
setup_logging()
logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events with comprehensive startup/shutdown"""
    # Startup
    logger.info("Starting up RAG System API...")
    logger.info(f"Configuration: Debug={settings.debug}, Hot Reload={settings.enable_hot_reload}")
    
    try:
        # Initialize database
        await init_db()
        logger.info("Database initialized")
        
        # Start periodic health checks
        health_check_task = asyncio.create_task(
            health_checker.run_health_checks_periodically()
        )
        logger.info("Health check system started")
        
        # Log startup completion
        logger.info("RAG System API startup completed successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        raise
    
    finally:
        # Shutdown
        logger.info("Shutting down RAG System API...")
        
        try:
            # Cancel health check task
            if 'health_check_task' in locals():
                health_check_task.cancel()
                try:
                    await health_check_task
                except asyncio.CancelledError:
                    pass
            
            # Close database connections
            await close_db()
            logger.info("Database connections closed")
            
            # Cleanup configuration watcher
            settings.cleanup()
            logger.info("Configuration system cleaned up")
            
        except Exception as e:
            logger.error(f"Shutdown error: {e}", exc_info=True)
        
        logger.info("RAG System API shutdown completed")


# Create FastAPI app
app = FastAPI(
    title=settings.project_name,
    description="RAG System API for document processing and chat",
    version="1.0.0",
    openapi_url=f"{settings.api_v1_str}/openapi.json",
    docs_url=f"{settings.api_v1_str}/docs",
    redoc_url=f"{settings.api_v1_str}/redoc",
    lifespan=lifespan
)

# Setup middleware
app.add_middleware(LoggingMiddleware)
setup_cors(app)
setup_security_headers(app)

# Include API router
app.include_router(api_router, prefix=settings.api_v1_str)


# Basic health check endpoint (detailed health checks are in admin API)
@app.get("/health")
async def basic_health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy", 
        "service": "rag-system-api",
        "timestamp": settings._last_reload.isoformat() if hasattr(settings, '_last_reload') else None
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "RAG System API",
        "version": "1.0.0",
        "docs": f"{settings.api_v1_str}/docs"
    }


# Enhanced exception handlers with structured logging
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions with logging"""
    logger.warning(
        f"HTTP exception: {exc.status_code} - {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail, 
            "status_code": exc.status_code,
            "path": request.url.path
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed logging"""
    logger.warning(
        f"Validation error on {request.method} {request.url.path}",
        extra={
            "errors": exc.errors(),
            "path": request.url.path,
            "method": request.method
        }
    )
    
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "errors": exc.errors(),
            "status_code": 422,
            "path": request.url.path
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions with comprehensive logging"""
    logger.error(
        f"Unhandled exception: {str(exc)}",
        exc_info=True,
        extra={
            "exception_type": type(exc).__name__,
            "path": request.url.path,
            "method": request.method,
            "client_ip": request.client.host if request.client else None
        }
    )
    
    if settings.debug:
        return JSONResponse(
            status_code=500,
            content={
                "detail": str(exc),
                "type": type(exc).__name__,
                "status_code": 500,
                "path": request.url.path
            }
        )
    else:
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "status_code": 500,
                "path": request.url.path
            }
        )