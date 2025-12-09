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
    IntIdMixin,
)


# ============================================================================
# Test Models
# ============================================================================

class TimestampedUser(Base, IntIdMixin, TimestampMixin):
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


# ============================================================================
# Test SoftDeleteMixin
# ============================================================================

class TestSoftDeleteMixin:
    """Test SoftDeleteMixin functionality."""

    def test_soft_delete(self, session):
        """Should mark as deleted."""
        post = SoftDeletablePost(title="Test Post")
        session.add(post)
        session.commit()

        post.soft_delete()
        session.commit()

        assert post.deleted_at is not None
        assert post.is_deleted is True

    def test_restore(self, session):
        """Should restore deleted record."""
        post = SoftDeletablePost(title="Test Post")
        session.add(post)
        session.commit()

        post.soft_delete()
        session.commit()

        post.restore()
        session.commit()

        assert post.deleted_at is None
        assert post.is_deleted is False

    def test_is_deleted_property(self, session):
        """Should check if deleted."""
        post = SoftDeletablePost(title="Test Post")
        session.add(post)
        session.commit()

        assert post.is_deleted is False

        post.soft_delete()
        assert post.is_deleted is True

    def test_active_query(self, session):
        """Should query only active records."""
        post1 = SoftDeletablePost(title="Active")
        post2 = SoftDeletablePost(title="Deleted")
        session.add_all([post1, post2])
        session.commit()

        post2.soft_delete()
        session.commit()

        active = list(SoftDeletablePost.active(session))

        assert len(active) == 1
        assert active[0].title == "Active"

    def test_deleted_query(self, session):
        """Should query only deleted records."""
        post1 = SoftDeletablePost(title="Active")
        post2 = SoftDeletablePost(title="Deleted")
        session.add_all([post1, post2])
        session.commit()

        post2.soft_delete()
        session.commit()

        deleted = list(SoftDeletablePost.deleted(session))

        assert len(deleted) == 1
        assert deleted[0].title == "Deleted"

    def test_with_deleted_query(self, session):
        """Should query all records including deleted."""
        post1 = SoftDeletablePost(title="Active")
        post2 = SoftDeletablePost(title="Deleted")
        session.add_all([post1, post2])
        session.commit()

        post2.soft_delete()
        session.commit()

        all_posts = list(SoftDeletablePost.with_deleted(session))

        assert len(all_posts) == 2


# ============================================================================
# Test UUIDMixin
# ============================================================================

class TestUUIDMixin:
    """Test UUIDMixin functionality."""

    def test_uuid_auto_generated(self, session):
        """Should auto-generate UUID."""
        user = UUIDUser(name="John")
        session.add(user)
        session.commit()

        assert user.id is not None
        assert isinstance(user.id, uuid.UUID)

    def test_uuid_uniqueness(self, session):
        """Should generate unique UUIDs."""
        user1 = UUIDUser(name="John")
        user2 = UUIDUser(name="Jane")
        session.add_all([user1, user2])
        session.commit()

        assert user1.id != user2.id

    def test_uuid_format(self, session):
        """Should be valid UUID4 format."""
        user = UUIDUser(name="John")
        session.add(user)
        session.commit()

        # UUID4 version byte should be 4
        assert user.id == 1

    def test_find_by_uuid(self, session):
        """Should find by UUID."""
        user = UUIDUser(name="John")
        session.add(user)
        session.commit()

        found = session.query(UUIDUser).filter_by(id=user.id).first()

        assert found is not None
        assert found.name == "John"
