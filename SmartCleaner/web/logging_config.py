"""
Structured logging configuration
All logs are JSON-formatted for better aggregation and searching
"""

import logging
import logging.config
import os
from pythonjsonlogger import jsonlogger
from datetime import datetime


class CustomJSONFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional context"""
    
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp
        log_record['timestamp'] = datetime.utcnow().isoformat()
        
        # Add log level
        log_record['level'] = record.levelname
        
        # Add logger name
        log_record['logger'] = record.name
        
        # Add function info
        log_record['function'] = record.funcName
        log_record['line'] = record.lineno
        
        # Add process/thread info for debugging
        if os.getenv('DEBUG_LOGGING', 'false').lower() == 'true':
            log_record['process_id'] = record.process
            log_record['thread_id'] = record.thread


def setup_logging(app):
    """Configure structured logging for Flask app"""
    
    log_level = app.config.get('LOG_LEVEL', 'INFO')
    log_format = app.config.get('LOG_FORMAT', 'json')
    
    # Remove default Flask logger handler
    app.logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level))
    
    if log_format == 'json':
        formatter = CustomJSONFormatter(
            '%(timestamp)s %(level)s %(name)s %(message)s'
        )
    else:
        # Plain text format
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    console_handler.setFormatter(formatter)
    
    # Add handler to app logger
    app.logger.addHandler(console_handler)
    app.logger.setLevel(getattr(logging, log_level))
    
    # Set up loggers for key modules
    for logger_name in ['werkzeug', 'flask', 'flask_cors']:
        logger = logging.getLogger(logger_name)
        logger.setLevel(getattr(logging, log_level))
        logger.handlers.clear()
        logger.addHandler(console_handler)
        logger.propagate = False
    
    return console_handler


def get_logger(name):
    """Get a logger for a specific module"""
    logger = logging.getLogger(name)
    
    # Only add handler if not already present
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(CustomJSONFormatter('%(timestamp)s %(level)s %(name)s %(message)s'))
        logger.addHandler(handler)
    
    return logger


# Convenience logging functions
def log_error(message, **kwargs):
    """Log an error with context"""
    logger = logging.getLogger('smart_data_cleaner')
    logger.error(message, extra=kwargs)


def log_warning(message, **kwargs):
    """Log a warning with context"""
    logger = logging.getLogger('smart_data_cleaner')
    logger.warning(message, extra=kwargs)


def log_info(message, **kwargs):
    """Log info with context"""
    logger = logging.getLogger('smart_data_cleaner')
    logger.info(message, extra=kwargs)


def log_debug(message, **kwargs):
    """Log debug info with context"""
    logger = logging.getLogger('smart_data_cleaner')
    logger.debug(message, extra=kwargs)
