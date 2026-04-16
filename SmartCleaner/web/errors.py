"""
Error handling utilities and custom exceptions
Provides consistent error responses across the API
"""

from flask import jsonify
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base application error"""
    
    def __init__(self, message, error_code, status_code=500, details=None):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class ValidationError(AppError):
    """Input validation error"""
    def __init__(self, message, details=None):
        super().__init__(message, 'VALIDATION_ERROR', 400, details)


class FileProcessingError(AppError):
    """Error during file processing"""
    def __init__(self, message, details=None):
        super().__init__(message, 'FILE_PROCESSING_ERROR', 400, details)


class NotFoundError(AppError):
    """Resource not found"""
    def __init__(self, message):
        super().__init__(message, 'NOT_FOUND', 404)


class UnauthorizedError(AppError):
    """Unauthorized access"""
    def __init__(self, message="Unauthorized"):
        super().__init__(message, 'UNAUTHORIZED', 401)


class RateLimitError(AppError):
    """Rate limit exceeded"""
    def __init__(self):
        super().__init__(
            "Rate limit exceeded. Please try again later.",
            'RATE_LIMIT_EXCEEDED',
            429
        )


class TimeoutError(AppError):
    """Request timeout"""
    def __init__(self):
        super().__init__(
            "Operation timed out. File may be too large.",
            'OPERATION_TIMEOUT',
            504
        )


def error_handler(app):
    """Register error handlers with Flask app"""
    
    @app.errorhandler(AppError)
    def handle_app_error(error):
        """Handle custom application errors"""
        response = {
            'success': False,
            'error': error.message,
            'error_code': error.error_code,
            'details': error.details
        }
        logger.warning(f"Application error: {error.error_code} - {error.message}")
        return jsonify(response), error.status_code
    
    @app.errorhandler(400)
    def handle_bad_request(error):
        """Handle 400 Bad Request"""
        response = {
            'success': False,
            'error': 'Bad request',
            'error_code': 'BAD_REQUEST'
        }
        return jsonify(response), 400
    
    @app.errorhandler(404)
    def handle_not_found(error):
        """Handle 404 Not Found"""
        response = {
            'success': False,
            'error': 'Endpoint not found',
            'error_code': 'NOT_FOUND'
        }
        return jsonify(response), 404
    
    @app.errorhandler(500)
    def handle_internal_error(error):
        """Handle 500 Internal Server Error"""
        logger.error(f"Internal server error: {str(error)}", exc_info=True)
        response = {
            'success': False,
            'error': 'Internal server error',
            'error_code': 'INTERNAL_ERROR'
        }
        return jsonify(response), 500
    
    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """Handle unexpected errors"""
        logger.error(f"Unexpected error: {str(error)}", exc_info=True)
        response = {
            'success': False,
            'error': 'An unexpected error occurred',
            'error_code': 'UNEXPECTED_ERROR'
        }
        return jsonify(response), 500


def handle_exceptions(f):
    """Decorator to handle exceptions in route handlers"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except AppError:
            raise  # Let error_handler deal with it
        except Exception as e:
            logger.error(f"Error in {f.__name__}: {str(e)}", exc_info=True)
            return jsonify({
                'success': False,
                'error': 'An error occurred processing your request',
                'error_code': 'PROCESSING_ERROR'
            }), 500
    return decorated_function
