"""
Comprehensive tests for FastKit Core Database Mixins.

Tests all mixins:
- TimestampMixin
- SoftDeleteMixin
- UUIDMixin
- SlugMixin
- PublishableMixin

"""

import pytest
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine, String
from sqlalchemy.orm import sessionmaker, Mapped, mapped_column

from fastkit_core.database import (
    Base,
    BaseWithTimestamps,
    TimestampMixin,
    SoftDeleteMixin,
    UUIDMixin,
    SlugMixin,
    PublishableMixin,
)


# ============================================================================
# Test Models
# ============================================================================

class TimestampedUser(Base, TimestampMixin):
    """User with timestamps."""
    name: Mapped[str] = mapped_column(String(100))


class SoftDeletablePost(Base, SoftDeleteMixin):
    """Post with soft delete."""
    title: Mapped[str] = mapped_column(String(200))


class UUIDUser(Base, UUIDMixin):
    """User with UUID primary key."""
    __tablename__ = 'uuid_users'
    name: Mapped[str] = mapped_column(String(100))


class SluggedArticle(Base, SlugMixin):
    """Article with slug."""
    title: Mapped[str] = mapped_column(String(200))


class PublishablePost(Base, PublishableMixin):
    """Post with publishing workflow."""
    title: Mapped[str] = mapped_column(String(200))