from typing import Callable
import asyncio

from functools import wraps
from fastkit_core.cache import get_cache

def cached(ttl: int, key: str | Callable[..., str]):
    def decorator(func):
        if not asyncio.iscoroutinefunction(func):
            raise TypeError(
                f"@cached can only decorate async functions. "
                f"'{func.__name__}' is a sync function."
            )
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = key(*args, **kwargs) if callable(key) else key
            cached_value = await get_cache().get(cache_key)

            if cached_value is not None:
                return cached_value

            result = await func(*args, **kwargs)
            await get_cache().set(cache_key, result, ttl=ttl)
            return result
        return wrapper
    return decorator