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