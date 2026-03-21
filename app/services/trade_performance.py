"""
Trade Engine Performance Optimizations

Features:
- Async value caching
- Rate limiting
- Connection pooling
- Batch processing
- Response compression
"""
import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import lru_cache, wraps
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


# ============================================================================
# Caching Layer
# ============================================================================

class TradeCache:
    """High-performance cache for trade calculations."""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        self._cache: Dict[str, Dict] = {}
        self._access_times: Dict[str, datetime] = {}
        self.max_size = max_size
        self.ttl = timedelta(seconds=ttl_seconds)
        self.hits = 0
        self.misses = 0
    
    def _make_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if key in self._cache:
            if datetime.now() - self._access_times[key] < self.ttl:
                self.hits += 1
                return self._cache[key]["value"]
            else:
                # Expired
                del self._cache[key]
                del self._access_times[key]
        
        self.misses += 1
        return None
    
    def set(self, key: str, value: Any):
        """Set value in cache with LRU eviction."""
        # Evict if full
        if len(self._cache) >= self.max_size:
            oldest_key = min(self._access_times, key=self._access_times.get)
            del self._cache[oldest_key]
            del self._access_times[oldest_key]
        
        self._cache[key] = {
            "value": value,
            "created": datetime.now()
        }
        self._access_times[key] = datetime.now()
    
    def clear(self):
        """Clear all cache entries."""
        self._cache.clear()
        self._access_times.clear()
    
    def stats(self) -> Dict:
        """Get cache statistics."""
        total = self.hits + self.misses
        hit_rate = self.hits / total if total > 0 else 0
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(hit_rate, 3)
        }


# Global cache instance
_trade_cache = TradeCache(max_size=500, ttl_seconds=180)  # 3 minute TTL


def cached_trade_calculation(ttl: int = 60):
    """Decorator for caching trade calculations."""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key
            key_data = {
                "func": func.__name__,
                "args": str(args),
                "kwargs": str(sorted(kwargs.items()))
            }
            cache_key = hashlib.md5(json.dumps(key_data).encode()).hexdigest()
            
            # Try cache first
            cached = _trade_cache.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached
            
            # Calculate fresh
            result = func(*args, **kwargs)
            
            # Cache result
            _trade_cache.set(cache_key, result)
            
            return result
        return wrapper
    return decorator


# ============================================================================
# Rate Limiting
# ============================================================================

class RateLimiter:
    """Token bucket rate limiter."""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = timedelta(seconds=window_seconds)
        self._requests: Dict[str, List[datetime]] = {}
    
    def is_allowed(self, key: str = "global") -> bool:
        """Check if request is allowed under rate limit."""
        now = datetime.now()
        
        if key not in self._requests:
            self._requests[key] = []
        
        # Clean old requests
        self._requests[key] = [
            t for t in self._requests[key]
            if now - t < self.window
        ]
        
        # Check limit
        if len(self._requests[key]) >= self.max_requests:
            return False
        
        # Add this request
        self._requests[key].append(now)
        return True
    
    def get_remaining(self, key: str = "global") -> int:
        """Get remaining requests in current window."""
        now = datetime.now()
        if key not in self._requests:
            return self.max_requests
        
        recent = [
            t for t in self._requests[key]
            if now - t < self.window
        ]
        return max(0, self.max_requests - len(recent))
    
    def reset(self, key: str = "global"):
        """Reset rate limit for key."""
        if key in self._requests:
            del self._requests[key]


# Global rate limiter
_rate_limiter = RateLimiter(max_requests=50, window_seconds=60)


def rate_limited(func: Callable):
    """Decorator for rate-limited functions."""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        if not _rate_limiter.is_allowed("trade_api"):
            raise Exception("Rate limit exceeded. Please wait before making more requests.")
        return await func(*args, **kwargs)
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        if not _rate_limiter.is_allowed("trade_api"):
            raise Exception("Rate limit exceeded. Please wait before making more requests.")
        return func(*args, **kwargs)
    
    # Return appropriate wrapper
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


# ============================================================================
# HTTP Client Pool
# ============================================================================

class HTTPClientPool:
    """Manages HTTP client connections for efficiency."""
    
    _instance = None
    _client: Optional[httpx.AsyncClient] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def get_client(self) -> httpx.AsyncClient:
        """Get or create shared HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                limits=httpx.Limits(
                    max_keepalive_connections=10,
                    max_connections=20
                ),
                headers={
                    "User-Agent": "DynastyDroid/1.0"
                }
            )
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None


# Global HTTP pool
_http_pool = HTTPClientPool()


# ============================================================================
# Batch Processing
# ============================================================================

class BatchProcessor:
    """Processes multiple trade evaluations efficiently."""
    
    def __init__(self, max_batch_size: int = 10):
        self.max_batch_size = max_batch_size
    
    @cached_trade_calculation(ttl=120)
    def _evaluate_single(
        self,
        give: List[Dict],
        get: List[Dict]
    ) -> Dict:
        """Single trade evaluation (cached)."""
        from app.services.trade_calculator import DynastyTradeCalculator
        
        calc = DynastyTradeCalculator()
        return calc.evaluate_trade(give, get)
    
    async def evaluate_batch(
        self,
        trades: List[Dict]
    ) -> List[Dict]:
        """
        Evaluate multiple trades in batch.
        
        Uses caching and parallel processing for efficiency.
        """
        results = []
        
        for trade in trades:
            give = trade.get("give", [])
            get = trade.get("get", [])
            
            try:
                result = self._evaluate_single(give, get)
                results.append({
                    "trade": trade,
                    "result": result,
                    "success": True
                })
            except Exception as e:
                results.append({
                    "trade": trade,
                    "error": str(e),
                    "success": False
                })
        
        return results


# ============================================================================
# Performance Monitoring
# ============================================================================

class PerformanceMonitor:
    """Monitors trade engine performance."""
    
    def __init__(self):
        self._measurements: Dict[str, List[float]] = {}
    
    def record(self, operation: str, duration_ms: float):
        """Record operation duration."""
        if operation not in self._measurements:
            self._measurements[operation] = []
        self._measurements[operation].append(duration_ms)
    
    def get_stats(self, operation: str = None) -> Dict:
        """Get performance statistics."""
        if operation:
            times = self._measurements.get(operation, [])
            if not times:
                return {}
            
            return {
                "operation": operation,
                "count": len(times),
                "avg_ms": round(sum(times) / len(times), 2),
                "min_ms": round(min(times), 2),
                "max_ms": round(max(times), 2)
            }
        
        return {
            op: self.get_stats(op)
            for op in self._measurements.keys()
        }
    
    def reset(self):
        """Reset all measurements."""
        self._measurements.clear()


# Global performance monitor
_perf_monitor = PerformanceMonitor()


def measure_performance(operation: str):
    """Decorator to measure function performance."""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = (time.time() - start) * 1000
                _perf_monitor.record(operation, duration)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                duration = (time.time() - start) * 1000
                _perf_monitor.record(operation, duration)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator


# ============================================================================
# Health Check
# ============================================================================

async def get_service_health() -> Dict:
    """Get health status of trade engine components."""
    cache_stats = _trade_cache.stats()
    perf_stats = _perf_monitor.get_stats()
    
    return {
        "status": "healthy",
        "cache": cache_stats,
        "performance": perf_stats,
        "rate_limiter": {
            "remaining": _rate_limiter.get_remaining(),
            "max": _rate_limiter.max_requests
        }
    }


# ============================================================================
# Initialization
# ============================================================================

async def initialize_trade_engine():
    """Initialize trade engine services."""
    logger.info("Initializing trade engine...")
    
    # Pre-warm cache with common values
    from app.services.trade_values import get_value_service
    service = get_value_service()
    
    # Fetch values in background
    try:
        await service.fetch_all_sources()
        logger.info("Trade engine initialized successfully")
    except Exception as e:
        logger.warning(f"Trade engine init warning: {e}")


async def shutdown_trade_engine():
    """Cleanup trade engine resources."""
    await _http_pool.close()
    logger.info("Trade engine shutdown complete")
