"""
Prometheus Monitoring Metrics for Smart Data Cleaner
Phase 4: DevOps & Monitoring
"""

from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest
from functools import wraps
import time
import logging

logger = logging.getLogger(__name__)

# Application Information
app_info = Info('smart_data_cleaner', 'Smart Data Cleaner Application')
app_info.info({'version': '1.0.0', 'environment': 'production'})

# Request Metrics
request_count = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0)
)

# Upload Metrics
files_uploaded = Counter(
    'files_uploaded_total',
    'Total files uploaded',
    ['file_type']
)

upload_size_bytes = Histogram(
    'file_upload_size_bytes',
    'File upload size in bytes',
    ['file_type'],
    buckets=(1000, 10000, 100000, 1000000, 10000000, 100000000)
)

# Data Processing Metrics
rows_processed = Counter(
    'rows_processed_total',
    'Total rows processed',
    ['operation']
)

processing_duration = Histogram(
    'processing_duration_seconds',
    'Data processing duration',
    ['operation'],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 25.0, 50.0)
)

data_quality_score = Gauge(
    'data_quality_score',
    'Average data quality score'
)

# Error Metrics
errors_total = Counter(
    'errors_total',
    'Total errors',
    ['error_type', 'endpoint']
)

exceptions_total = Counter(
    'exceptions_total',
    'Total exceptions',
    ['exception_type']
)

# Session Metrics
active_sessions = Gauge(
    'active_sessions',
    'Number of active sessions'
)

session_duration = Histogram(
    'session_duration_seconds',
    'Session duration in seconds',
    buckets=(60, 300, 600, 1800, 3600, 7200)
)

# Rate Limiting Metrics
rate_limit_exceeded = Counter(
    'rate_limit_exceeded_total',
    'Rate limit exceeded count',
    ['client_id']
)

# Cache Metrics
cache_hits = Counter(
    'cache_hits_total',
    'Cache hits'
)

cache_misses = Counter(
    'cache_misses_total',
    'Cache misses'
)

# Database Metrics
db_query_duration = Histogram(
    'db_query_duration_seconds',
    'Database query duration',
    ['query_type'],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0)
)

db_connections = Gauge(
    'db_connections',
    'Number of database connections'
)

# Memory and Resource Metrics
memory_usage_bytes = Gauge(
    'memory_usage_bytes',
    'Memory usage in bytes'
)

cpu_usage_percent = Gauge(
    'cpu_usage_percent',
    'CPU usage percentage'
)

# Business Metrics
cleaning_operations = Counter(
    'cleaning_operations_total',
    'Total cleaning operations',
    ['operation_type']
)

export_operations = Counter(
    'export_operations_total',
    'Total export operations',
    ['export_format']
)


def track_request(f):
    """Decorator to track HTTP request metrics"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        status = 200
        
        try:
            result = f(*args, **kwargs)
            return result
        except Exception as e:
            status = 500
            raise
        finally:
            duration = time.time() - start_time
            
            from flask import request
            method = request.method
            endpoint = request.endpoint or 'unknown'
            
            request_count.labels(method=method, endpoint=endpoint, status=status).inc()
            request_duration.labels(method=method, endpoint=endpoint).observe(duration)
    
    return decorated_function


def track_processing(operation_type):
    """Decorator to track data processing metrics"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = f(*args, **kwargs)
                
                # Track row count if result is a DataFrame
                if hasattr(result, '__len__'):
                    rows_processed.labels(operation=operation_type).inc(len(result))
                
                return result
            finally:
                duration = time.time() - start_time
                processing_duration.labels(operation=operation_type).observe(duration)
        
        return decorated_function
    return decorator


def get_metrics():
    """Get all metrics in Prometheus format"""
    return generate_latest()


class MetricsCollector:
    """Collect and update application metrics"""
    
    @staticmethod
    def update_system_metrics():
        """Update CPU and memory metrics"""
        import psutil
        
        process = psutil.Process()
        memory_usage_bytes.set(process.memory_info().rss)
        cpu_usage_percent.set(process.cpu_percent(interval=1))
    
    @staticmethod
    def update_session_count(count):
        """Update active session count"""
        active_sessions.set(count)
    
    @staticmethod
    def update_quality_score(score):
        """Update average data quality score"""
        data_quality_score.set(score)
    
    @staticmethod
    def record_upload(file_type, file_size):
        """Record file upload"""
        files_uploaded.labels(file_type=file_type).inc()
        upload_size_bytes.labels(file_type=file_type).observe(file_size)
    
    @staticmethod
    def record_error(error_type, endpoint):
        """Record error occurrence"""
        errors_total.labels(error_type=error_type, endpoint=endpoint).inc()
    
    @staticmethod
    def record_cache_hit():
        """Record cache hit"""
        cache_hits.inc()
    
    @staticmethod
    def record_cache_miss():
        """Record cache miss"""
        cache_misses.inc()


# Prometheus configuration for docker-compose
PROMETHEUS_CONFIG = """
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'smart-data-cleaner'
    static_configs:
      - targets: ['localhost:5000']
    metrics_path: '/metrics'
"""


# Grafana dashboard JSON
GRAFANA_DASHBOARD = {
    "dashboard": {
        "title": "Smart Data Cleaner",
        "panels": [
            {
                "title": "HTTP Requests",
                "targets": [
                    {"expr": "rate(http_requests_total[5m])"}
                ]
            },
            {
                "title": "Request Duration",
                "targets": [
                    {"expr": "histogram_quantile(0.95, http_request_duration_seconds_bucket)"}
                ]
            },
            {
                "title": "Data Quality Score",
                "targets": [
                    {"expr": "data_quality_score"}
                ]
            },
            {
                "title": "Error Rate",
                "targets": [
                    {"expr": "rate(errors_total[5m])"}
                ]
            },
            {
                "title": "Active Sessions",
                "targets": [
                    {"expr": "active_sessions"}
                ]
            },
            {
                "title": "Memory Usage",
                "targets": [
                    {"expr": "memory_usage_bytes"}
                ]
            }
        ]
    }
}
