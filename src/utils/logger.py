"""
Centralized logging configuration for YouTube Shorts automation.
Provides structured logging with file rotation and color-coded console output.
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime
import sys


# ANSI color codes for console output
class LogColors:
    RESET = '\033[0m'
    DEBUG = '\033[36m'  # Cyan
    INFO = '\033[32m'   # Green
    WARNING = '\033[33m'  # Yellow
    ERROR = '\033[31m'  # Red
    CRITICAL = '\033[35m'  # Magenta


class ColoredFormatter(logging.Formatter):
    """Custom formatter with color-coded output for console."""
    
    COLORS = {
        'DEBUG': LogColors.DEBUG,
        'INFO': LogColors.INFO,
        'WARNING': LogColors.WARNING,
        'ERROR': LogColors.ERROR,
        'CRITICAL': LogColors.CRITICAL,
    }
    
    def format(self, record):
        # Add color to levelname
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{LogColors.RESET}"
        
        return super().format(record)


def setup_logger(
    name: str = 'youtubeshorts',
    level: str = 'INFO',
    log_dir: str = None
) -> logging.Logger:
    """
    Setup structured logger with file and console output.
    
    Args:
        name: Logger name (default: 'youtubeshorts')
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files (default: ./logs)
    
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Set log level
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # Create log directory
    if log_dir is None:
        log_dir = os.path.join(os.getcwd(), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # File handler with rotation (10MB max, keep 5 backups)
    log_file = os.path.join(log_dir, f'{name}.log')
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    
    # File formatter (detailed)
    file_formatter = logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)s | %(filename)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # Console formatter (colored, concise)
    console_formatter = ColoredFormatter(
        '%(levelname)s | %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def get_logger(name: str = 'youtubeshorts') -> logging.Logger:
    """
    Get or create a logger instance.
    
    Args:
        name: Logger name
    
    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    
    # If logger doesn't have handlers, set it up
    if not logger.handlers:
        return setup_logger(name)
    
    return logger


# Performance tracking decorator
def log_performance(logger: logging.Logger = None):
    """
    Decorator to log function execution time.
    
    Usage:
        @log_performance()
        def my_function():
            pass
    """
    import time
    import functools
    
    if logger is None:
        logger = get_logger()
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                logger.info(f"⏱️ {func.__name__} completed in {elapsed:.2f}s")
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(f"❌ {func.__name__} failed after {elapsed:.2f}s: {e}")
                raise
        return wrapper
    return decorator


# Global logger instance
_default_logger = None


def get_default_logger() -> logging.Logger:
    """Get the default logger instance."""
    global _default_logger
    if _default_logger is None:
        _default_logger = setup_logger()
    return _default_logger
