"""
Unit tests for cursor_paginated_response.

Coverage:
- Basic structure and response format
- Serialization: plain dicts, Pydantic v2, SQLAlchemy-like models, nested structures
- Cursor and has_next logic
- Optional message field
- Custom status codes
- Edge cases: empty list, None cursor, large pages
"""

import json
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

from fastkit_core.http.responses import cursor_paginated_response


# ============================================================================
# Helpers
# ============================================================================

def _body(response) -> dict:
    """Parse JSONResponse body."""
    return json.loads(response.body)


class UserSchema(BaseModel):
    """Pydantic v2 schema used in serialization tests."""

    id: int
    name: str


def _make_orm_instance(id_: int, name: str) -> MagicMock:
    """
    Simulate a minimal SQLAlchemy model instance.

    _serialize checks for __table__.columns, so we fake that structure
    without pulling in SQLAlchemy itself.
    """
    col_id = MagicMock()
    col_id.name = "id"
    col_name = MagicMock()
    col_name.name = "name"

    instance = MagicMock()
    instance.__table__ = MagicMock()
    instance.__table__.columns = [col_id, col_name]
    instance.id = id_
    instance.name = name

    # Pydantic checks must NOT match — ensure no model_dump / dict attribute
    del instance.model_dump
    del instance.dict

    return instance


# ============================================================================
# Response structure
# ============================================================================

class TestCursorPaginatedResponseStructure:
    """Top-level shape of cursor_paginated_response."""

    def test_returns_json_response(self):
        """Should return a JSONResponse instance."""
        from starlette.responses import JSONResponse

        response = cursor_paginated_response(items=[], next_cursor=None, per_page=20)

        assert isinstance(response, JSONResponse)

    def test_success_flag_is_true(self):
        """success field must always be True."""
        response = cursor_paginated_response(items=[], next_cursor=None, per_page=20)

        assert _body(response)["success"] is True

    def test_data_key_present(self):
        """data key must be present."""
        response = cursor_paginated_response(items=[], next_cursor=None, per_page=20)

        assert "data" in _body(response)

    def test_pagination_key_present(self):
        """pagination key must be present."""
        response = cursor_paginated_response(items=[], next_cursor=None, per_page=20)

        assert "pagination" in _body(response)

    def test_pagination_contains_required_keys(self):
        """pagination must contain next_cursor, per_page, has_next."""
        response = cursor_paginated_response(
            items=[], next_cursor="abc", per_page=10
        )
        pagination = _body(response)["pagination"]

        assert "next_cursor" in pagination
        assert "per_page" in pagination
        assert "has_next" in pagination

    def test_default_status_code_is_200(self):
        """Default HTTP status must be 200."""
        response = cursor_paginated_response(items=[], next_cursor=None, per_page=20)

        assert response.status_code == 200


# ============================================================================
# Cursor and has_next logic
# ============================================================================

class TestCursorAndHasNext:
    """Cursor forwarding and has_next derivation."""

    def test_next_cursor_forwarded_when_provided(self):
        """next_cursor value must appear in pagination."""
        cursor = "eyJpZCI6IDIwfQ=="
        response = cursor_paginated_response(
            items=[], next_cursor=cursor, per_page=20
        )

        assert _body(response)["pagination"]["next_cursor"] == cursor

    def test_next_cursor_is_none_on_last_page(self):
        """next_cursor must be None when no further pages exist."""
        response = cursor_paginated_response(items=[], next_cursor=None, per_page=20)

        assert _body(response)["pagination"]["next_cursor"] is None

    def test_has_next_true_when_cursor_present(self):
        """has_next must be True when next_cursor is not None."""
        response = cursor_paginated_response(
            items=[], next_cursor="some_cursor", per_page=20
        )

        assert _body(response)["pagination"]["has_next"] is True

    def test_has_next_false_when_cursor_is_none(self):
        """has_next must be False when next_cursor is None."""
        response = cursor_paginated_response(items=[], next_cursor=None, per_page=20)

        assert _body(response)["pagination"]["has_next"] is False

    def test_per_page_forwarded(self):
        """per_page value must appear unchanged in pagination."""
        response = cursor_paginated_response(items=[], next_cursor=None, per_page=50)

        assert _body(response)["pagination"]["per_page"] == 50


# ============================================================================
# Optional message
# ============================================================================

class TestMessageField:
    """Presence and absence of the optional message field."""

    def test_message_included_when_provided(self):
        """message key must appear when argument is given."""
        response = cursor_paginated_response(
            items=[], next_cursor=None, per_page=20, message="OK"
        )

        assert _body(response)["message"] == "OK"

    def test_message_absent_by_default(self):
        """message key must NOT appear when not provided."""
        response = cursor_paginated_response(items=[], next_cursor=None, per_page=20)

        assert "message" not in _body(response)

    def test_message_absent_when_none(self):
        """message key must NOT appear when explicitly passed as None."""
        response = cursor_paginated_response(
            items=[], next_cursor=None, per_page=20, message=None
        )

        assert "message" not in _body(response)


# ============================================================================
# Custom status code
# ============================================================================

class TestStatusCode:
    """HTTP status code forwarding."""

    def test_custom_status_code(self):
        """Should use provided status code."""
        response = cursor_paginated_response(
            items=[], next_cursor=None, per_page=20, status_code=206
        )

        assert response.status_code == 206

    def test_status_code_does_not_affect_body(self):
        """Body structure must be the same regardless of status code."""
        r200 = cursor_paginated_response(items=[], next_cursor=None, per_page=20)
        r206 = cursor_paginated_response(
            items=[], next_cursor=None, per_page=20, status_code=206
        )

        body_200 = _body(r200)
        body_206 = _body(r206)

        assert body_200["success"] == body_206["success"]
        assert body_200["data"] == body_206["data"]
        assert body_200["pagination"] == body_206["pagination"]


# ============================================================================
# Item serialization — plain dicts
# ============================================================================

class TestSerializationPlainDicts:
    """Items that are already plain dicts should pass through unchanged."""

    def test_plain_dict_items_passed_through(self):
        """Plain dicts must appear verbatim in data."""
        items = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
        response = cursor_paginated_response(
            items=items, next_cursor=None, per_page=20
        )

        assert _body(response)["data"] == items

    def test_item_count_preserved(self):
        """Number of items in data must match input list length."""
        items = [{"id": i} for i in range(7)]
        response = cursor_paginated_response(
            items=items, next_cursor=None, per_page=20
        )

        assert len(_body(response)["data"]) == 7


# ============================================================================
# Item serialization — Pydantic v2
# ============================================================================

class TestSerializationPydantic:
    """Pydantic model instances must be serialized via model_dump()."""

    def test_pydantic_model_serialized(self):
        """Pydantic v2 instances must be converted to dicts."""
        items = [UserSchema(id=1, name="Alice"), UserSchema(id=2, name="Bob")]
        response = cursor_paginated_response(
            items=items, next_cursor=None, per_page=20
        )

        data = _body(response)["data"]
        assert data == [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]

    def test_pydantic_model_fields_present(self):
        """All model fields must appear in the serialized dict."""
        items = [UserSchema(id=42, name="Charlie")]
        response = cursor_paginated_response(
            items=items, next_cursor=None, per_page=20
        )

        item = _body(response)["data"][0]
        assert item["id"] == 42
        assert item["name"] == "Charlie"


# ============================================================================
# Item serialization — SQLAlchemy-like ORM models
# ============================================================================

class TestSerializationORM:
    """ORM instances with __table__.columns must be serialized to dicts."""

    def test_orm_instance_serialized(self):
        """ORM instance must be converted using __table__.columns."""
        orm_instance = _make_orm_instance(id_=10, name="Dave")
        response = cursor_paginated_response(
            items=[orm_instance], next_cursor=None, per_page=20
        )

        data = _body(response)["data"]
        assert data == [{"id": 10, "name": "Dave"}]

    def test_multiple_orm_instances(self):
        """Multiple ORM instances must all be serialized."""
        items = [_make_orm_instance(i, f"User{i}") for i in range(3)]
        response = cursor_paginated_response(
            items=items, next_cursor=None, per_page=20
        )

        data = _body(response)["data"]
        assert len(data) == 3
        assert data[0] == {"id": 0, "name": "User0"}


# ============================================================================
# Item serialization — nested structures
# ============================================================================

class TestSerializationNested:
    """Nested Pydantic / ORM objects inside dicts and lists must be serialized."""

    def test_nested_pydantic_in_dict(self):
        """Pydantic model nested inside a dict value must be serialized."""
        items = [{"user": UserSchema(id=1, name="Eve"), "token": "abc"}]
        response = cursor_paginated_response(
            items=items, next_cursor=None, per_page=20
        )

        item = _body(response)["data"][0]
        assert item["user"] == {"id": 1, "name": "Eve"}
        assert item["token"] == "abc"

    def test_nested_pydantic_in_list_value(self):
        """List of Pydantic models nested inside a dict must be fully serialized."""
        items = [
            {
                "users": [
                    UserSchema(id=1, name="Alice"),
                    UserSchema(id=2, name="Bob"),
                ]
            }
        ]
        response = cursor_paginated_response(
            items=items, next_cursor=None, per_page=20
        )

        users = _body(response)["data"][0]["users"]
        assert users == [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]


# ============================================================================
# Edge cases
# ============================================================================

class TestEdgeCases:
    """Boundary conditions and unusual inputs."""

    def test_empty_items_list(self):
        """Empty items list must produce an empty data array."""
        response = cursor_paginated_response(items=[], next_cursor=None, per_page=20)

        assert _body(response)["data"] == []

    def test_per_page_of_one(self):
        """per_page=1 is a valid boundary value."""
        response = cursor_paginated_response(
            items=[{"id": 1}], next_cursor="cursor", per_page=1
        )

        body = _body(response)
        assert body["pagination"]["per_page"] == 1
        assert len(body["data"]) == 1

    def test_large_per_page(self):
        """Large per_page values must be forwarded without truncation."""
        response = cursor_paginated_response(
            items=[], next_cursor=None, per_page=1000
        )

        assert _body(response)["pagination"]["per_page"] == 1000

    def test_items_with_none_values(self):
        """Items containing None field values must serialize cleanly."""
        items = [{"id": 1, "name": None}]
        response = cursor_paginated_response(
            items=items, next_cursor=None, per_page=20
        )

        assert _body(response)["data"] == [{"id": 1, "name": None}]

    def test_cursor_with_special_characters(self):
        """Cursor strings with base64 padding must be preserved exactly."""
        cursor = "eyJpZCI6IDIwfQ=="
        response = cursor_paginated_response(
            items=[], next_cursor=cursor, per_page=20
        )

        assert _body(response)["pagination"]["next_cursor"] == cursor

    def test_no_extra_keys_in_pagination(self):
        """pagination block must contain exactly the three documented keys."""
        response = cursor_paginated_response(
            items=[], next_cursor=None, per_page=20
        )
        pagination_keys = set(_body(response)["pagination"].keys())

        assert pagination_keys == {"next_cursor", "per_page", "has_next"}