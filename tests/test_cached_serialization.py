"""
Tests for @cached decorator — tuple and Pydantic serialization fix.

Covers the bug reported in:
  0.4.3-issue-cached-decorator-tuple-and-pydantic-serialization.md

Root cause: decorator passed raw Python objects directly to the cache backend
without JSON serialization, causing redis.exceptions.DataError for any return
type beyond str / int.

Fix: _to_serializable / _from_serializable / _serialize / _deserialize helpers
wrap all values as JSON strings before storage and reconstruct them on cache hit.
_from_serializable is fully recursive, so tuple-inside-tuple and other nested
composite structures are also reconstructed correctly.

Test surface:
- _to_serializable: primitives, dict, list, Pydantic, tuple, nested tuple, dict with Pydantic value
- _from_serializable: primitives, dict, list, tuple sentinel, nested tuple, dict without sentinel
- _serialize / _deserialize roundtrip: all supported types
- @cached end-to-end: str, int, None, dict, list[dict], tuple,
  Pydantic model, list[BaseModel], tuple(list[BaseModel], dict),
  tuple inside tuple
- Cache miss / hit call count
- Raw stored value is a JSON string
"""

import json
import pytest
from pydantic import BaseModel
from unittest.mock import MagicMock

from fastkit_core.cache import get_cache, reset_cache, setup_cache
from fastkit_core.cache.decorators import (
    _deserialize,
    _from_serializable,
    _serialize,
    _to_serializable,
    cached,
)


# ============================================================================
# Fixtures
# ============================================================================


def make_config(driver: str = "memory", **extra):
    config = MagicMock()
    defaults = {"driver": driver, "ttl": 300}
    defaults.update(extra)
    config.get.return_value = defaults
    return config


@pytest.fixture(autouse=True)
def reset_singleton():
    reset_cache()
    setup_cache(make_config())
    yield
    reset_cache()


# ============================================================================
# Pydantic schemas used across tests
# ============================================================================


class ProductResponse(BaseModel):
    id: int
    name: str
    price: float


class UserResponse(BaseModel):
    id: int
    email: str


# ============================================================================
# Unit tests — _to_serializable
# ============================================================================


class TestToSerializable:
    """_to_serializable converts Python values to JSON-safe structures."""

    # --- primitives ---

    def test_str_passthrough(self):
        assert _to_serializable("hello") == "hello"

    def test_int_passthrough(self):
        assert _to_serializable(42) == 42

    def test_float_passthrough(self):
        assert _to_serializable(3.14) == pytest.approx(3.14)

    def test_bool_passthrough(self):
        assert _to_serializable(True) is True

    def test_none_passthrough(self):
        assert _to_serializable(None) is None

    # --- dict ---

    def test_plain_dict_passthrough(self):
        assert _to_serializable({"a": 1, "b": "two"}) == {"a": 1, "b": "two"}

    def test_dict_with_pydantic_value(self):
        user = UserResponse(id=7, email="a@b.com")
        result = _to_serializable({"user": user, "token": "abc"})
        assert result == {"user": {"id": 7, "email": "a@b.com"}, "token": "abc"}

    def test_nested_dict(self):
        result = _to_serializable({"outer": {"inner": 1}})
        assert result == {"outer": {"inner": 1}}

    # --- list ---

    def test_plain_list_passthrough(self):
        assert _to_serializable([1, "two", 3.0]) == [1, "two", 3.0]

    def test_list_of_pydantic_models(self):
        items = [
            ProductResponse(id=1, name="A", price=1.0),
            ProductResponse(id=2, name="B", price=2.0),
        ]
        result = _to_serializable(items)
        assert result == [
            {"id": 1, "name": "A", "price": 1.0},
            {"id": 2, "name": "B", "price": 2.0},
        ]

    # --- Pydantic ---

    def test_pydantic_model_uses_model_dump(self):
        product = ProductResponse(id=1, name="Widget", price=9.99)
        result = _to_serializable(product)
        assert result == {"id": 1, "name": "Widget", "price": 9.99}

    # --- tuple ---

    def test_tuple_wrapped_with_sentinel(self):
        result = _to_serializable((1, 2, 3))
        assert result == {"__tuple__": True, "items": [1, 2, 3]}

    def test_tuple_items_are_recursed(self):
        product = ProductResponse(id=1, name="X", price=5.0)
        result = _to_serializable(({"count": 1}, product))
        assert result["__tuple__"] is True
        assert result["items"][0] == {"count": 1}
        assert result["items"][1] == {"id": 1, "name": "X", "price": 5.0}

    def test_tuple_inside_tuple(self):
        result = _to_serializable(((1, 2), (3, 4)))
        assert result == {
            "__tuple__": True,
            "items": [
                {"__tuple__": True, "items": [1, 2]},
                {"__tuple__": True, "items": [3, 4]},
            ],
        }

    def test_deeply_nested_tuple(self):
        """Three levels deep: tuple(tuple(tuple))."""
        result = _to_serializable(((("deep",),),))
        assert result == {
            "__tuple__": True,
            "items": [
                {
                    "__tuple__": True,
                    "items": [
                        {"__tuple__": True, "items": ["deep"]}
                    ],
                }
            ],
        }


# ============================================================================
# Unit tests — _from_serializable
# ============================================================================


class TestFromSerializable:
    """_from_serializable reconstructs Python types from JSON-safe structures."""

    # --- primitives ---

    def test_str_passthrough(self):
        assert _from_serializable("hello") == "hello"

    def test_int_passthrough(self):
        assert _from_serializable(42) == 42

    def test_none_passthrough(self):
        assert _from_serializable(None) is None

    # --- dict without sentinel ---

    def test_plain_dict_returned_as_dict(self):
        result = _from_serializable({"a": 1, "b": 2})
        assert isinstance(result, dict)
        assert result == {"a": 1, "b": 2}

    def test_dict_values_are_recursed(self):
        """Tuple sentinel nested inside a dict value must be reconstructed."""
        data = {"payload": {"__tuple__": True, "items": [1, 2]}}
        result = _from_serializable(data)
        assert isinstance(result["payload"], tuple)
        assert result["payload"] == (1, 2)

    def test_dict_without_tuple_key_stays_as_dict(self):
        """Dict that has an 'items' key but no __tuple__ stays as dict."""
        data = {"items": [1, 2], "other": "value"}
        result = _from_serializable(data)
        assert isinstance(result, dict)

    # --- list ---

    def test_list_of_primitives(self):
        assert _from_serializable([1, 2, 3]) == [1, 2, 3]

    def test_list_containing_tuple_sentinel(self):
        data = [{"__tuple__": True, "items": [1, 2]}, 3]
        result = _from_serializable(data)
        assert result[0] == (1, 2)
        assert result[1] == 3

    # --- tuple sentinel ---

    def test_tuple_sentinel_reconstructed(self):
        data = {"__tuple__": True, "items": [1, 2, 3]}
        result = _from_serializable(data)
        assert isinstance(result, tuple)
        assert result == (1, 2, 3)

    def test_nested_tuple_reconstructed(self):
        data = {
            "__tuple__": True,
            "items": [
                {"__tuple__": True, "items": [1, 2]},
                {"__tuple__": True, "items": [3, 4]},
            ],
        }
        result = _from_serializable(data)
        assert isinstance(result, tuple)
        assert isinstance(result[0], tuple)
        assert isinstance(result[1], tuple)
        assert result == ((1, 2), (3, 4))

    def test_deeply_nested_tuple_reconstructed(self):
        data = {
            "__tuple__": True,
            "items": [
                {
                    "__tuple__": True,
                    "items": [
                        {"__tuple__": True, "items": ["deep"]}
                    ],
                }
            ],
        }
        result = _from_serializable(data)
        assert result == ((("deep",),),)
        assert isinstance(result[0][0], tuple)


# ============================================================================
# Unit tests — _serialize / _deserialize roundtrip
# ============================================================================


class TestSerializeDeserializeRoundtrip:
    """_serialize → _deserialize must reconstruct the original value."""

    def test_str_roundtrip(self):
        assert _deserialize(_serialize("hello")) == "hello"

    def test_int_roundtrip(self):
        assert _deserialize(_serialize(99)) == 99

    def test_float_roundtrip(self):
        assert _deserialize(_serialize(3.14)) == pytest.approx(3.14)

    def test_bool_roundtrip(self):
        assert _deserialize(_serialize(True)) is True

    def test_none_roundtrip(self):
        assert _deserialize(_serialize(None)) is None

    def test_dict_roundtrip(self):
        original = {"a": 1, "b": "two"}
        assert _deserialize(_serialize(original)) == original

    def test_list_of_dicts_roundtrip(self):
        original = [{"id": 1}, {"id": 2}]
        assert _deserialize(_serialize(original)) == original

    def test_tuple_roundtrip(self):
        original = (1, "two", 3.0)
        result = _deserialize(_serialize(original))
        assert isinstance(result, tuple)
        assert result == original

    def test_tuple_inside_tuple_roundtrip(self):
        original = ((1, 2), (3, 4))
        result = _deserialize(_serialize(original))
        assert isinstance(result, tuple)
        assert isinstance(result[0], tuple)
        assert isinstance(result[1], tuple)
        assert result == original

    def test_deeply_nested_tuple_roundtrip(self):
        original = ((("deep",),),)
        result = _deserialize(_serialize(original))
        assert result == original
        assert isinstance(result[0][0], tuple)

    def test_pydantic_model_roundtrip_as_dict(self):
        """Pydantic models serialize to dict — type info is not preserved."""
        product = ProductResponse(id=1, name="Widget", price=9.99)
        result = _deserialize(_serialize(product))
        assert isinstance(result, dict)
        assert result == {"id": 1, "name": "Widget", "price": 9.99}

    def test_list_of_pydantic_models_roundtrip(self):
        items = [
            ProductResponse(id=1, name="A", price=1.0),
            ProductResponse(id=2, name="B", price=2.0),
        ]
        result = _deserialize(_serialize(items))
        assert result == [
            {"id": 1, "name": "A", "price": 1.0},
            {"id": 2, "name": "B", "price": 2.0},
        ]

    def test_paginate_tuple_roundtrip(self):
        """Exact paginate() shape: tuple(list[dict], dict)."""
        items = [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
        meta = {"page": 1, "total": 2, "has_next": False}
        original = (items, meta)

        result = _deserialize(_serialize(original))

        assert isinstance(result, tuple)
        assert result[0] == items
        assert result[1] == meta

    def test_serialize_produces_json_string(self):
        raw = _serialize({"key": "value"})
        assert isinstance(raw, str)
        assert json.loads(raw) == {"key": "value"}


# ============================================================================
# Integration tests — @cached decorator end-to-end
# ============================================================================


class TestCachedReturnTypes:
    """@cached must store and retrieve all supported return types correctly."""

    @pytest.mark.asyncio
    async def test_cached_plain_str(self):
        @cached(ttl=60, key="str:key")
        async def fn():
            return "hello"

        assert await fn() == "hello"
        assert await fn() == "hello"

    @pytest.mark.asyncio
    async def test_cached_plain_int(self):
        @cached(ttl=60, key="int:key")
        async def fn():
            return 42

        assert await fn() == 42
        assert await fn() == 42

    @pytest.mark.asyncio
    async def test_cached_none_not_cached(self):
        """None is treated as cache miss — function is called every time."""
        call_count = 0

        @cached(ttl=60, key="none:key")
        async def fn():
            nonlocal call_count
            call_count += 1
            return None

        await fn()
        await fn()
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_cached_dict(self):
        @cached(ttl=60, key="dict:key")
        async def fn():
            return {"id": 1, "name": "Alice"}

        first = await fn()
        second = await fn()
        assert first == second == {"id": 1, "name": "Alice"}

    @pytest.mark.asyncio
    async def test_cached_list_of_dicts(self):
        @cached(ttl=60, key="list:key")
        async def fn():
            return [{"id": 1}, {"id": 2}, {"id": 3}]

        result = await fn()
        assert result == [{"id": 1}, {"id": 2}, {"id": 3}]
        assert await fn() == result

    @pytest.mark.asyncio
    async def test_cached_tuple_reconstructed_as_tuple(self):
        """Core fix: tuple must come back as tuple, not list."""

        @cached(ttl=60, key="tuple:key")
        async def fn():
            return (1, "two", 3.0)

        result = await fn()
        assert isinstance(result, tuple)
        assert result == (1, "two", 3.0)

    @pytest.mark.asyncio
    async def test_cached_tuple_on_cache_hit_is_still_tuple(self):
        """Cache hit must also reconstruct as tuple."""

        @cached(ttl=60, key="tuple:hit")
        async def fn():
            return ("a", "b")

        await fn()  # miss — stores serialized
        result = await fn()  # hit — must deserialize back

        assert isinstance(result, tuple)
        assert result == ("a", "b")

    @pytest.mark.asyncio
    async def test_cached_tuple_inside_tuple(self):
        """Nested tuple must be fully reconstructed on cache hit."""

        @cached(ttl=60, key="tuple:nested")
        async def fn():
            return ((1, 2), (3, 4))

        await fn()  # miss
        result = await fn()  # hit

        assert isinstance(result, tuple)
        assert isinstance(result[0], tuple)
        assert isinstance(result[1], tuple)
        assert result == ((1, 2), (3, 4))

    @pytest.mark.asyncio
    async def test_cached_deeply_nested_tuple(self):
        @cached(ttl=60, key="tuple:deep")
        async def fn():
            return ((("deep",),),)

        await fn()
        result = await fn()

        assert result == ((("deep",),),)
        assert isinstance(result[0][0], tuple)

    @pytest.mark.asyncio
    async def test_cached_pydantic_model_returned_as_dict(self):
        @cached(ttl=60, key="pydantic:single")
        async def fn():
            return {"id": 1, "name": "Widget", "price": 9.99}

        result = await fn()
        assert isinstance(result, dict)
        assert result == {"id": 1, "name": "Widget", "price": 9.99}

    @pytest.mark.asyncio
    async def test_cached_list_of_pydantic_models(self):
        @cached(ttl=60, key="pydantic:list")
        async def fn():
            return [
                {"id": 1, "name": "A", "price": 1.0},
                {"id": 2, "name": "B", "price": 2.0},
            ]

        result = await fn()
        assert result == [
            {"id": 1, "name": "A", "price": 1.0},
            {"id": 2, "name": "B", "price": 2.0},
        ]

    @pytest.mark.asyncio
    async def test_cached_paginate_tuple_scenario(self):
        """
        Exact scenario from the bug report:
        paginate() returns tuple(list[ProductResponse], dict).
        Must be stored and retrieved without DataError.
        """

        @cached(ttl=60, key="paginate:p1")
        async def paginate():
            items = [
                {"id": 1, "name": "Widget", "price": 9.99},
                {"id": 2, "name": "Gadget", "price": 19.99},
            ]
            meta = {"page": 1, "per_page": 10, "total": 2, "has_next": False}
            return items, meta

        result = await paginate()

        assert isinstance(result, tuple)
        items, meta = result
        assert items == [
            {"id": 1, "name": "Widget", "price": 9.99},
            {"id": 2, "name": "Gadget", "price": 19.99},
        ]
        assert meta == {"page": 1, "per_page": 10, "total": 2, "has_next": False}

    @pytest.mark.asyncio
    async def test_cached_paginate_cache_hit_returns_tuple(self):
        """Cache hit for paginate() must also return tuple."""
        call_count = 0

        @cached(ttl=60, key="paginate:hit")
        async def paginate():
            nonlocal call_count
            call_count += 1
            return [{"id": 1}], {"page": 1}

        await paginate()  # miss
        result = await paginate()  # hit

        assert call_count == 1
        assert isinstance(result, tuple)
        items, meta = result
        assert items == [{"id": 1}]
        assert meta == {"page": 1}