from typing import Callable, Any
import asyncio
import json
from pydantic import BaseModel

from functools import wraps
from fastkit_core.cache import get_cache

def _to_serializable(item):
    if isinstance(item, BaseModel):  # Pydantic v2
        return item.model_dump()
    if isinstance(item, tuple):
        return {'__tuple__': True, 'items': [_to_serializable(i) for i in item]}
    if isinstance(item, list):
        return [_to_serializable(i) for i in item]
    if isinstance(item, dict):
        return {k: _to_serializable(v) for k, v in item.items()}
    return item  # str, int, float, bool, None — already JSON-safe

def _from_serializable(item: Any) -> Any:
    """Recursively reconstruct Python types from JSON-safe structures."""
    if isinstance(item, dict):
        if item.get("__tuple__"):
            # Reconstruct tuple — recurse into each item
            return tuple(_from_serializable(i) for i in item["items"])
        # Regular dict — recurse into values
        return {k: _from_serializable(v) for k, v in item.items()}
    if isinstance(item, list):
        return [_from_serializable(i) for i in item]
    # Primitive — str, int, float, bool, None
    return item

def _serialize(value) -> str:
    """Serialize any supported value to a JSON string."""
    return json.dumps(_to_serializable(value))

def _deserialize(raw: str):
    """Deserialize a JSON string back to its original structure."""
    data = json.loads(raw)
    return _from_serializable(data)

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
            cached_raw = await get_cache().get(cache_key)
            if cached_raw is not None:
                return _deserialize(cached_raw)
            result = await func(*args, **kwargs)
            await get_cache().set(cache_key, _serialize(result), ttl=ttl)
            return result
        return wrapper
    return decorator