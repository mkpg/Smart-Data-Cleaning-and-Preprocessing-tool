"""
Security utilities for Smart Data Cleaner
Includes CSRF protection, secure headers, and input sanitization
"""

from flask import request, jsonify
from functools import wraps
import secrets
import logging
from html import escape

logger = logging.getLogger(__name__)


class SecurityHeaders:
    """Security headers to add to responses"""
    
    HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self'",
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Permissions-Policy': 'geolocation=(), microphone=(), camera=()'
    }
    
    @staticmethod
    def apply(response):
        """Apply security headers to Flask response"""
        for header, value in SecurityHeaders.HEADERS.items():
            response.headers[header] = value
        return response


def require_https(f):
    """Decorator to require HTTPS in production"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.headers.get('X-Forwarded-Proto', 'http') == 'http':
            import os
            if os.getenv('FLASK_ENV') == 'production':
                logger.warning(f"Non-HTTPS request to {request.path} blocked")
                return jsonify({
                    'success': False,
                    'error': 'HTTPS required',
                    'error_code': 'HTTPS_REQUIRED'
                }), 403
        return f(*args, **kwargs)
    return decorated_function


class CSRFProtection:
    """CSRF token generation and validation"""
    
    TOKEN_LENGTH = 32
    
    @staticmethod
    def generate_token():
        """Generate a secure CSRF token"""
        return secrets.token_urlsafe(CSRFProtection.TOKEN_LENGTH)
    
    @staticmethod
    def validate_token(token_from_request, token_from_session):
        """Validate CSRF token using constant-time comparison"""
        if not token_from_request or not token_from_session:
            return False
        
        return secrets.compare_digest(token_from_request, token_from_session)
    
    @staticmethod
    def require_csrf(f):
        """Decorator to validate CSRF token on state-changing requests"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Only validate for POST, PUT, DELETE, PATCH
            if request.method not in ['POST', 'PUT', 'DELETE', 'PATCH']:
                return f(*args, **kwargs)
            
            # Get token from either header or form data
            token_from_request = (
                request.headers.get('X-CSRF-Token') or
                request.form.get('csrf_token') or
                request.get_json({}).get('csrf_token')
            )
            
            # Get token from session
            from flask import session
            token_from_session = session.get('csrf_token')
            
            if not token_from_session:
                logger.warning(f"CSRF: No token in session for {request.path}")
                return jsonify({
                    'success': False,
                    'error': 'CSRF validation failed',
                    'error_code': 'CSRF_VALIDATION_FAILED'
                }), 403
            
            if not CSRFProtection.validate_token(token_from_request, token_from_session):
                logger.warning(f"CSRF: Token mismatch for {request.path} from {request.remote_addr}")
                return jsonify({
                    'success': False,
                    'error': 'CSRF validation failed',
                    'error_code': 'CSRF_VALIDATION_FAILED'
                }), 403
            
            return f(*args, **kwargs)
        return decorated_function


class InputSanitizer:
    """Sanitize user input to prevent XSS and injection attacks"""
    
    @staticmethod
    def sanitize_string(value, max_length=1000):
        """Sanitize string input"""
        if not isinstance(value, str):
            return value
        
        # Limit length
        if len(value) > max_length:
            value = value[:max_length]
        
        # Escape HTML entities
        return escape(value)
    
    @staticmethod
    def sanitize_filename(filename, max_length=255):
        """Sanitize filename to prevent path traversal"""
        # Remove path separators and special characters
        import os
        import re
        
        filename = os.path.basename(filename)  # Remove any path components
        filename = re.sub(r'[^\w\s\-.]', '', filename)  # Remove special chars
        filename = filename[:max_length]  # Limit length
        
        if not filename:
            filename = 'file'
        
        return filename
    
    @staticmethod
    def sanitize_json(data):
        """Sanitize JSON data recursively"""
        if isinstance(data, dict):
            return {
                InputSanitizer.sanitize_string(k): InputSanitizer.sanitize_json(v)
                for k, v in data.items()
            }
        elif isinstance(data, list):
            return [InputSanitizer.sanitize_json(item) for item in data]
        elif isinstance(data, str):
            return InputSanitizer.sanitize_string(data)
        else:
            return data


class RateLimitConfig:
    """Rate limiting configuration"""
    
    LIMITS = {
        '/api/v1/upload': ('10 per minute', 'file_upload'),
        '/api/v1/execute': ('5 per minute', 'execute_cleaning'),
        '/api/v1/export': ('20 per minute', 'export_data'),
        '/api/v1/*': ('100 per hour', 'global')
    }
    
    @staticmethod
    def get_limit_key(endpoint):
        """Get rate limit key for an endpoint"""
        return RateLimitConfig.LIMITS.get(endpoint, ('100 per hour', 'default'))


def setup_security(app):
    """Configure all security features for Flask app"""
    
    # Force HTTPS in production
    if app.config.get('REQUIRE_HTTPS'):
        @app.before_request
        def enforce_https():
            if request.headers.get('X-Forwarded-Proto', 'http') == 'http':
                from flask import redirect
                url = request.url.replace('http://', 'https://', 1)
                return redirect(url, code=301)
    
    # Add security headers to all responses
    @app.after_request
    def add_security_headers(response):
        return SecurityHeaders.apply(response)
    
    # Generate and store CSRF token for session
    @app.before_request
    def generate_csrf_token():
        from flask import session
        if 'csrf_token' not in session:
            session['csrf_token'] = CSRFProtection.generate_token()
    
    logger.info("Security features initialized")
