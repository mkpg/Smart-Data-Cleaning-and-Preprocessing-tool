"""
Configuration management for Smart Data Cleaner
Supports environment-specific settings for dev/test/prod
"""

import os
from datetime import timedelta

class Config:
    """Base configuration with defaults"""
    
    # Flask
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'sqlite:///smart_data_cleaner.db'  # Development default
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session Management
    SESSION_TYPE = os.getenv('SESSION_TYPE', 'filesystem')
    SESSION_REDIS = os.getenv('REDIS_URL', 'redis://localhost:6379')
    PERMANENT_SESSION_LIFETIME = timedelta(
        hours=int(os.getenv('SESSION_LIFETIME_HOURS', 24))
    )
    
    # File Upload
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', './uploads')
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_FILE_SIZE_MB', 50)) * 1024 * 1024
    ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}
    
    # Security
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')
    REQUIRE_HTTPS = os.getenv('REQUIRE_HTTPS', 'False').lower() == 'true'
    
    # Rate Limiting
    RATELIMIT_STORAGE_URL = os.getenv('REDIS_URL', 'memory://')
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = 'json'  # 'json' or 'text'
    
    # Sentry (Error Tracking)
    SENTRY_DSN = os.getenv('SENTRY_DSN', None)
    
    # API
    API_VERSION = 'v1'
    API_PREFIX = f'/api/{API_VERSION}'
    
    # Timeouts
    REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT_SECONDS', 300))
    FILE_PARSE_TIMEOUT = int(os.getenv('FILE_PARSE_TIMEOUT_SECONDS', 120))


class DevelopmentConfig(Config):
    """Development environment configuration"""
    DEBUG = True
    SQLALCHEMY_ECHO = True
    LOG_LEVEL = 'DEBUG'


class TestingConfig(Config):
    """Testing environment configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    """Production environment configuration"""
    DEBUG = False
    REQUIRE_HTTPS = True
    # In production, all critical config must come from environment
    # No defaults should be used


# Select configuration based on environment
config_name = os.getenv('FLASK_ENV', 'development')
configs = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig
}

current_config = configs.get(config_name, DevelopmentConfig)
