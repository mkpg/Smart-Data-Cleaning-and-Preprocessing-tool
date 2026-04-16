"""
Performance Optimization Module for Smart Data Cleaner
Phase 5: Performance Optimization
Caching, query optimization, and resource management
"""

import functools
import time
import hashlib
import json
from typing import Any, Callable, Optional
import logging

logger = logging.getLogger(__name__)


class CacheStrategy:
    """Caching strategies for different data types"""
    
    # In-memory cache (can be replaced with Redis)
    _cache = {}
    _cache_times = {}
    
    DEFAULT_TTL = 300  # 5 minutes
    
    @classmethod
    def cache_key(cls, function_name: str, *args, **kwargs) -> str:
        """Generate cache key from function and arguments"""
        key_data = f"{function_name}:{str(args)}:{str(sorted(kwargs.items()))}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    @classmethod
    def get(cls, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key in cls._cache:
            cached_time = cls._cache_times.get(key, 0)
            age = time.time() - cached_time
            
            if age < cls.DEFAULT_TTL:
                logger.debug(f"Cache hit: {key}")
                return cls._cache[key]
            else:
                # Expired
                del cls._cache[key]
                del cls._cache_times[key]
        
        return None
    
    @classmethod
    def set(cls, key: str, value: Any, ttl: int = None):
        """Set value in cache"""
        cls._cache[key] = value
        cls._cache_times[key] = time.time()
        logger.debug(f"Cache set: {key}")
    
    @classmethod
    def clear(cls):
        """Clear all cache"""
        cls._cache.clear()
        cls._cache_times.clear()
        logger.info("Cache cleared")
    
    @classmethod
    def size(cls) -> int:
        """Get cache size in bytes"""
        total = 0
        for key, value in cls._cache.items():
            total += len(str(key)) + len(str(value))
        return total


def cached_result(ttl: int = CacheStrategy.DEFAULT_TTL):
    """Decorator to cache function results"""
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = CacheStrategy.cache_key(f.__name__, *args, **kwargs)
            
            # Check cache
            cached = CacheStrategy.get(cache_key)
            if cached is not None:
                return cached
            
            # Call function
            result = f(*args, **kwargs)
            
            # Cache result
            CacheStrategy.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator


class QueryOptimization:
    """Database query optimization strategies"""
    
    @staticmethod
    def use_indexes(columns: list) -> list:
        """Recommend indexes for frequently queried columns"""
        return [f"CREATE INDEX idx_{col} ON data({col});" for col in columns]
    
    @staticmethod
    def limit_result_set(query: str, limit: int = 1000) -> str:
        """Add LIMIT clause to prevent large result sets"""
        if 'LIMIT' not in query.upper():
            return f"{query} LIMIT {limit}"
        return query
    
    @staticmethod
    def avoid_n_plus_one(queries: list) -> str:
        """Combine multiple queries into single batch query"""
        # Join queries into single bulk operation
        return "BEGIN; " + " ".join(queries) + " COMMIT;"
    
    @staticmethod
    def use_connection_pooling(max_connections: int = 10) -> dict:
        """Connection pooling configuration"""
        return {
            'max_connections': max_connections,
            'min_cached': 5,
            'max_cached': 10,
            'max_overflow': 10
        }


class DataCompressionStrategy:
    """Data compression for network efficiency"""
    
    @staticmethod
    def compress_response(data: Any, compression_type: str = 'gzip') -> bytes:
        """Compress response data"""
        import gzip
        
        json_data = json.dumps(data).encode('utf-8')
        
        if compression_type == 'gzip':
            return gzip.compress(json_data)
        elif compression_type == 'brotli':
            try:
                import brotli
                return brotli.compress(json_data)
            except ImportError:
                logger.warning("brotli not available, using gzip")
                return gzip.compress(json_data)
        
        return json_data
    
    @staticmethod
    def get_compression_header(compression_type: str) -> dict:
        """Get HTTP headers for compression"""
        return {
            'Content-Encoding': compression_type,
            'Vary': 'Accept-Encoding'
        }


class PandasOptimization:
    """Pandas DataFrame optimization"""
    
    @staticmethod
    def optimize_dtypes(df):
        """Reduce DataFrame memory usage by optimizing data types"""
        for col in df.columns:
            col_type = df[col].dtype
            
            # Optimize integers
            if 'int' in str(col_type):
                if df[col].min() >= 0:
                    if df[col].max() < 256:
                        df[col] = df[col].astype('uint8')
                    elif df[col].max() < 65536:
                        df[col] = df[col].astype('uint16')
                else:
                    if df[col].min() > -128 and df[col].max() < 127:
                        df[col] = df[col].astype('int8')
                    elif df[col].min() > -32768 and df[col].max() < 32767:
                        df[col] = df[col].astype('int16')
            
            # Optimize floats
            elif 'float' in str(col_type):
                df[col] = df[col].astype('float32')
            
            # Optimize object/string
            elif col_type == 'object':
                if df[col].nunique() / len(df) < 0.5:
                    df[col] = df[col].astype('category')
        
        logger.info(f"Optimized DataFrame: memory usage reduced")
        return df
    
    @staticmethod
    def use_chunking(file_path: str, chunk_size: int = 10000):
        """Process large files in chunks"""
        import pandas as pd
        chunks = []
        for chunk in pd.read_csv(file_path, chunksize=chunk_size):
            chunks.append(chunk)
        return chunks
    
    @staticmethod
    def use_dtype_specification(columns: dict):
        """Specify dtypes when reading CSV"""
        # Example: {'age': 'int32', 'name': 'string', 'salary': 'float32'}
        return columns


class AsyncProcessing:
    """Asynchronous processing for long-running tasks"""
    
    @staticmethod
    def queue_background_task(task_name: str, data: dict):
        """Queue background task (uses Celery/Redis)"""
        # Pseudo-code - implement with Celery
        logger.info(f"Queued background task: {task_name}")
        return {'task_id': 'task_123', 'status': 'queued'}
    
    @staticmethod
    def get_task_status(task_id: str):
        """Get background task status"""
        # Pseudo-code
        return {'task_id': task_id, 'status': 'processing', 'progress': 50}


class CDNStrategy:
    """CDN and static file optimization"""
    
    @staticmethod
    def optimize_static_assets():
        """Recommendations for static asset optimization"""
        return {
            'minify_css': True,
            'minify_js': True,
            'minify_html': True,
            'enable_compression': True,
            'set_cache_headers': True,
            'use_cdn': True
        }
    
    @staticmethod
    def get_cache_headers(asset_type: str) -> dict:
        """Get caching headers for static assets"""
        if asset_type == 'css':
            return {'Cache-Control': 'public, max-age=31536000'}
        elif asset_type == 'js':
            return {'Cache-Control': 'public, max-age=31536000'}
        elif asset_type == 'image':
            return {'Cache-Control': 'public, max-age=86400'}
        else:
            return {'Cache-Control': 'public, max-age=3600'}


class PerformanceMonitoring:
    """Monitor and profile application performance"""
    
    _metrics = {
        'avg_response_time': 0,
        'p95_response_time': 0,
        'p99_response_time': 0,
        'memory_peak': 0,
        'cpu_peak': 0
    }
    
    @staticmethod
    def profile_function(f: Callable) -> Callable:
        """Profile function execution"""
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            import cProfile
            import pstats
            from io import StringIO
            
            pr = cProfile.Profile()
            pr.enable()
            
            result = f(*args, **kwargs)
            
            pr.disable()
            s = StringIO()
            ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
            ps.print_stats(10)  # Top 10 functions
            
            logger.debug(s.getvalue())
            return result
        
        return wrapper
    
    @staticmethod
    def benchmark(f: Callable, iterations: int = 100) -> dict:
        """Benchmark function performance"""
        times = []
        
        for _ in range(iterations):
            start = time.time()
            f()
            times.append(time.time() - start)
        
        import statistics
        return {
            'mean': statistics.mean(times),
            'median': statistics.median(times),
            'stdev': statistics.stdev(times) if len(times) > 1 else 0,
            'min': min(times),
            'max': max(times)
        }


# Performance optimization recommendations
OPTIMIZATION_CHECKLIST = {
    'Caching': {
        'response_caching': False,
        'query_caching': False,
        'redis_integration': False,
    },
    'Database': {
        'use_indexes': False,
        'connection_pooling': False,
        'query_optimization': False,
    },
    'Frontend': {
        'minify_assets': False,
        'cdn_enabled': False,
        'compression_enabled': False,
    },
    'Data Processing': {
        'dtype_optimization': False,
        'chunked_processing': False,
        'async_operations': False,
    },
    'Monitoring': {
        'performance_metrics': False,
        'profiling_enabled': False,
        'benchmarking': False,
    }
}


def calculate_optimization_score():
    """Calculate performance optimization score"""
    total = sum(len(v) for v in OPTIMIZATION_CHECKLIST.values())
    completed = sum(1 for category in OPTIMIZATION_CHECKLIST.values() 
                   for status in category.values() if status)
    return (completed / total) * 100 if total > 0 else 0
