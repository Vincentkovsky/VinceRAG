"""
Comprehensive logging system with structured logging support
"""

import json
import logging
import logging.handlers
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from contextvars import ContextVar

from .config import settings

# Context variables for request tracking
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        # Base log entry
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add request context if available
        request_id = request_id_var.get()
        if request_id:
            log_entry["request_id"] = request_id
            
        user_id = user_id_var.get()
        if user_id:
            log_entry["user_id"] = user_id
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info)
            }
        
        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in {
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                'filename', 'module', 'lineno', 'funcName', 'created',
                'msecs', 'relativeCreated', 'thread', 'threadName',
                'processName', 'process', 'getMessage', 'exc_info',
                'exc_text', 'stack_info'
            }:
                log_entry[key] = value
        
        return json.dumps(log_entry, default=str, ensure_ascii=False)


class StandardFormatter(logging.Formatter):
    """Standard text formatter with colors for console output"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record: logging.LogRecord) -> str:
        # Add color for console output
        if hasattr(sys.stderr, 'isatty') and sys.stderr.isatty():
            color = self.COLORS.get(record.levelname, '')
            record.levelname = f"{color}{record.levelname}{self.RESET}"
        
        # Add request context
        request_id = request_id_var.get()
        user_id = user_id_var.get()
        
        context_parts = []
        if request_id:
            context_parts.append(f"req:{request_id[:8]}")
        if user_id:
            context_parts.append(f"user:{user_id}")
        
        context_str = f"[{' '.join(context_parts)}] " if context_parts else ""
        
        # Format message
        formatted = super().format(record)
        return f"{context_str}{formatted}"


def setup_logging():
    """Setup application logging configuration"""
    
    # Clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Set log level
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root_logger.setLevel(log_level)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    
    if settings.structured_logging:
        console_handler.setFormatter(StructuredFormatter())
    else:
        console_handler.setFormatter(StandardFormatter(
            fmt=settings.log_format,
            datefmt="%Y-%m-%d %H:%M:%S"
        ))
    
    root_logger.addHandler(console_handler)
    
    # File handler if specified
    if settings.log_file:
        log_path = Path(settings.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_path,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        
        # Always use structured format for file logs
        file_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(file_handler)
    
    # Configure specific loggers
    configure_loggers()
    
    logging.info("Logging system initialized")


def configure_loggers():
    """Configure specific logger levels and behavior"""
    
    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("watchdog").setLevel(logging.WARNING)
    
    # Set application loggers
    logging.getLogger("app").setLevel(log_level := getattr(logging, settings.log_level.upper()))
    logging.getLogger("app.services").setLevel(log_level)
    logging.getLogger("app.api").setLevel(log_level)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name"""
    return logging.getLogger(f"app.{name}")


def log_with_context(logger: logging.Logger, level: int, message: str, **kwargs):
    """Log a message with additional context"""
    extra = {
        "context": kwargs
    }
    logger.log(level, message, extra=extra)


def log_performance(logger: logging.Logger, operation: str, duration: float, **kwargs):
    """Log performance metrics"""
    log_with_context(
        logger,
        logging.INFO,
        f"Performance: {operation}",
        duration=duration,
        operation=operation,
        **kwargs
    )


def log_user_action(logger: logging.Logger, action: str, user_id: str, **kwargs):
    """Log user actions for audit trail"""
    log_with_context(
        logger,
        logging.INFO,
        f"User action: {action}",
        action=action,
        user_id=user_id,
        **kwargs
    )


def log_system_event(logger: logging.Logger, event: str, **kwargs):
    """Log system events"""
    log_with_context(
        logger,
        logging.INFO,
        f"System event: {event}",
        event=event,
        **kwargs
    )


def log_error_with_context(logger: logging.Logger, error: Exception, context: Dict[str, Any]):
    """Log error with additional context"""
    logger.error(
        f"Error: {str(error)}",
        exc_info=True,
        extra={"error_context": context}
    )


class LoggingContext:
    """Context manager for adding logging context"""
    
    def __init__(self, request_id: Optional[str] = None, user_id: Optional[str] = None):
        self.request_id = request_id
        self.user_id = user_id
        self.request_id_token = None
        self.user_id_token = None
    
    def __enter__(self):
        if self.request_id:
            self.request_id_token = request_id_var.set(self.request_id)
        if self.user_id:
            self.user_id_token = user_id_var.set(self.user_id)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.request_id_token:
            request_id_var.reset(self.request_id_token)
        if self.user_id_token:
            user_id_var.reset(self.user_id_token)