import os
import json
import redis
import hashlib
from typing import Any, Optional, Union, Callable
from functools import wraps
from loguru import logger

class CacheService:
    """Redis-based caching service."""
    
    _instance = None
    
    def __init__(self, redis_url: str = None):
        if redis_url is None:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        
        try:
            self.redis = redis.from_url(redis_url, decode_responses=True)
            self.redis.ping()
            self.enabled = True
            logger.info(f"Connected to Redis at {redis_url}")
        except redis.ConnectionError as e:
            logger.warning(f"Failed to connect to Redis: {e}. Caching disabled.")
            self.enabled = False
            self.redis = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.enabled:
            return None
        try:
            value = self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in cache with TTL (seconds)."""
        if not self.enabled:
            return False
        try:
            # Handle objects with to_dict method
            if hasattr(value, 'to_dict') and callable(value.to_dict):
                serialized = json.dumps(value.to_dict())
            # Handle Pydantic models
            elif hasattr(value, 'model_dump_json'):
                serialized = value.model_dump_json()
            elif hasattr(value, 'json') and callable(value.json): # Old pydantic
                serialized = value.json()
            else:
                serialized = json.dumps(value)
                
            self.redis.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    def generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate a stable cache key."""
        payload = f"{prefix}:{args}:{kwargs}"
        return hashlib.md5(payload.encode()).hexdigest()

def cache_response(ttl: int = 300, prefix: str = "cache", deserializer: Optional[callable] = None):
    """Decorator to cache function responses."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = CacheService.get_instance()
            if not cache.enabled:
                return func(*args, **kwargs)
            
            # Generate key based on args (skipping 'self' if method)
            try:
                # Handle instance methods by checking if first arg is self
                # But tricky to detect reliable "self".
                # Let's just key on function name + args
                key_content = f"{func.__module__}.{func.__name__}:{args}:{kwargs}"
                key = f"{prefix}:{hashlib.md5(key_content.encode()).hexdigest()}"
                
                cached_val = cache.get(key)
                if cached_val is not None:
                    if deserializer:
                        return deserializer(cached_val)
                    return cached_val
                
                result = func(*args, **kwargs)
                cache.set(key, result, ttl)
                return result
            except Exception as e:
                logger.warning(f"Cache decorator error: {e}. Skipping cache.")
                return func(*args, **kwargs)
        return wrapper
    return decorator
