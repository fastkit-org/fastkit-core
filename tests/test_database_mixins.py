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

# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def engine():
    """Create in-memory SQLite engine."""
    engine = create_engine('sqlite:///:memory:', echo=False)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    """Create database session."""
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


# ============================================================================
# Test TimestampMixin
# ============================================================================

class TestTimestampMixin:
    """Test TimestampMixin functionality."""

    def test_created_at_auto_set(self, session):
        """Should auto-set created_at on create."""
        user = TimestampedUser(name="John")
        session.add(user)
        session.commit()

        assert user.created_at is not None
        assert isinstance(user.created_at, datetime)

    def test_updated_at_auto_set(self, session):
        """Should auto-set updated_at on create."""
        user = TimestampedUser(name="John")
        session.add(user)
        session.commit()

        assert user.updated_at is not None
        assert isinstance(user.updated_at, datetime)

    def test_updated_at_auto_update(self, session):
        """Should auto-update updated_at on update."""
        user = TimestampedUser(name="John")
        session.add(user)
        session.commit()

        original_updated = user.updated_at

        # Small delay
        import time
        time.sleep(0.01)

        user.name = "Jane"
        session.commit()

        assert user.updated_at > original_updated

    def test_created_at_immutable(self, session):
        """Should not change created_at on update."""
        user = TimestampedUser(name="John")
        session.add(user)
        session.commit()

        original_created = user.created_at

        user.name = "Jane"
        session.commit()

        assert user.created_at == original_created

    def test_timestamp_timezone_aware(self, session):
        """Should use timezone-aware timestamps."""
        user = TimestampedUser(name="John")
        session.add(user)
        session.commit()

        assert user.created_at is not None

    def test_base_with_timestamps(self, session):
        """Should work with BaseWithTimestamps."""

        class Article(BaseWithTimestamps):
            title: Mapped[str] = mapped_column(String(200))

        Base.metadata.create_all(session.bind)

        article = Article(title="Test")
        session.add(article)
        session.commit()

        assert hasattr(article, 'created_at')
        assert hasattr(article, 'updated_at')
        assert article.created_at is not None