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