"""
Structured Logging Configuration
Provides JSON logging, context tracking, and monitoring setup
"""

import json
import logging
import sys
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Dict, Any, Optional
import traceback


class JsonFormatter(logging.Formatter):
    """
    Custom formatter that outputs JSON-formatted logs
    Useful for log aggregation and parsing (ELK, CloudWatch, etc.)
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        
        # Base log entry
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields if provided
        if hasattr(record, 'extra') and isinstance(record.extra, dict):
            log_entry.update(record.extra)
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exc()
            }
        
        # Add any additional attributes from the record
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName',
                          'levelname', 'levelno', 'lineno', 'module', 'msecs', 'message',
                          'pathname', 'process', 'processName', 'relativeCreated', 'thread',
                          'threadName', 'exc_info', 'exc_text', 'stack_info', 'getMessage',
                          'extra']:
                if not key.startswith('_'):
                    log_entry[key] = str(value)
        
        return json.dumps(log_entry, default=str)


class ContextFilter(logging.Filter):
    """
    Filter that adds contextual information to log records
    Useful for tracking requests, batches, etc.
    """
    
    # Thread-local context storage
    _context: Dict[str, Any] = {}
    
    @classmethod
    def set_context(cls, key: str, value: Any):
        """Set a context value"""
        cls._context[key] = value
    
    @classmethod
    def get_context(cls, key: str, default: Any = None) -> Any:
        """Get a context value"""
        return cls._context.get(key, default)
    
    @classmethod
    def clear_context(cls):
        """Clear all context"""
        cls._context.clear()
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add context to log record"""
        # Add batch_id if available
        batch_id = self._context.get('batch_id')
        if batch_id:
            record.batch_id = batch_id
        
        # Add request_id if available
        request_id = self._context.get('request_id')
        if request_id:
            record.request_id = request_id
        
        # Add user if available
        user = self._context.get('user')
        if user:
            record.user = user
        
        return True


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    use_json: bool = True,
    console_output: bool = True
) -> logging.Logger:
    """
    Setup structured logging configuration
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for log output
        use_json: Whether to use JSON formatting
        console_output: Whether to output to console
    
    Returns:
        Configured logger instance
    """
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add context filter
    context_filter = ContextFilter()
    
    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.addFilter(context_filter)
        
        if use_json:
            console_handler.setFormatter(JsonFormatter())
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(formatter)
        
        root_logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10485760,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(log_level)
        file_handler.addFilter(context_filter)
        
        if use_json:
            file_handler.setFormatter(JsonFormatter())
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
        
        root_logger.addHandler(file_handler)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance"""
    return logging.getLogger(name)


def log_with_context(
    logger: logging.Logger,
    level: str,
    message: str,
    **context
):
    """
    Log with additional context
    
    Args:
        logger: Logger instance
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        message: Log message
        **context: Additional context fields
    """
    log_method = getattr(logger, level.lower(), logger.info)
    log_method(message, extra=context)


# Default logging configuration for module
if __name__ == "__main__":
    # Example usage
    logger = setup_logging(
        log_level="INFO",
        log_file="app.log",
        use_json=True,
        console_output=True
    )
    
    # Set some context
    ContextFilter.set_context('batch_id', 'BATCH-001')
    ContextFilter.set_context('user', 'admin')
    
    # Test logging
    logger.info("Application started", extra={"version": "1.0.0"})
    logger.warning("Warning test", extra={"threshold": 95})
    logger.error("Error test", extra={"error_code": "ERR-001"})
    
    try:
        raise ValueError("Test exception")
    except Exception as e:
        logger.exception("Exception occurred", extra={"recovery": "retry"})
