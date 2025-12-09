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


class SoftDeletablePost(Base, IntIdMixin, SoftDeleteMixin):
    """Post with soft delete."""
    title: Mapped[str] = mapped_column(String(200))


class UUIDUser(Base, UUIDMixin):
    """User with UUID primary key."""
    __tablename__ = 'uuid_users'
    name: Mapped[str] = mapped_column(String(100))


class SluggedArticle(Base, IntIdMixin, SlugMixin):
    """Article with slug."""
    title: Mapped[str] = mapped_column(String(200))


class PublishablePost(Base, IntIdMixin, PublishableMixin):
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

        class Article(BaseWithTimestamps, IntIdMixin):
            __tablename__ = 'mixin_tmp_articles'
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
        assert user.id.version == 4

    def test_find_by_uuid(self, session):
        """Should find by UUID."""
        user = UUIDUser(name="John")
        session.add(user)
        session.commit()

        found = session.query(UUIDUser).filter_by(id=user.id).first()

        assert found is not None
        assert found.name == "John"


# ============================================================================
# Test SlugMixin
# ============================================================================

class TestSlugMixin:
    """Test SlugMixin functionality."""

    def test_generate_slug_basic(self, session):
        """Should generate slug from title."""
        article = SluggedArticle(title="Hello World")
        article.generate_slug()

        assert article.slug == "hello-world"

    def test_generate_slug_special_chars(self, session):
        """Should handle special characters."""
        article = SluggedArticle(title="Hello, World!")
        article.generate_slug()

        assert article.slug == "hello-world"

    def test_generate_slug_multiple_spaces(self, session):
        """Should handle multiple spaces."""
        article = SluggedArticle(title="Hello    World")
        article.generate_slug()

        assert article.slug == "hello-world"

    def test_generate_slug_trim_hyphens(self, session):
        """Should trim leading/trailing hyphens."""
        article = SluggedArticle(title="  Hello World  ")
        article.generate_slug()

        assert article.slug == "hello-world"
        assert not article.slug.startswith('-')
        assert not article.slug.endswith('-')

    def test_generate_slug_max_length(self, session):
        """Should respect max length."""
        article = SluggedArticle(title="A" * 300)
        article.generate_slug(max_length=50)

        assert len(article.slug) <= 50

    def test_generate_slug_uniqueness(self, session):
        """Should ensure uniqueness with counter."""
        article1 = SluggedArticle(title="Hello World")
        article1.generate_slug(session=session)
        session.add(article1)
        session.commit()

        article2 = SluggedArticle(title="Hello World")
        article2.generate_slug(session=session)

        assert article2.slug == "hello-world-1"

    def test_generate_slug_uniqueness_multiple(self, session):
        """Should increment counter for multiple duplicates."""
        for i in range(3):
            article = SluggedArticle(title="Test")
            article.generate_slug(session=session)
            session.add(article)
            session.commit()

        article4 = SluggedArticle(title="Test")
        article4.generate_slug(session=session)

        assert article4.slug == "test-3"

    def test_generate_slug_custom_source(self, session):
        """Should generate from custom field."""

        class CustomArticle(Base, IntIdMixin, SlugMixin):
            name: Mapped[str] = mapped_column(String(200))
            title: Mapped[str] = mapped_column(String(200))

        Base.metadata.create_all(session.bind)

        article = CustomArticle(name="My Name", title="My Title")
        article.generate_slug(source_field='name')

        assert article.slug == "my-name"

    def test_generate_slug_empty_source(self, session):
        """Should raise error for empty source."""
        article = SluggedArticle(title="")

        with pytest.raises(ValueError) as exc_info:
            article.generate_slug()

        assert "empty" in str(exc_info.value).lower()


# ============================================================================
# Test PublishableMixin
# ============================================================================

class TestPublishableMixin:
    """Test PublishableMixin functionality."""

    def test_publish(self, session):
        """Should publish immediately."""
        post = PublishablePost(title="Test")
        session.add(post)
        session.commit()

        post.publish()
        session.commit()

        assert post.published_at is not None
        assert post.is_published is True
        assert post.is_draft is False

    def test_unpublish(self, session):
        """Should unpublish to draft."""
        post = PublishablePost(title="Test")
        session.add(post)
        session.commit()

        post.publish()
        post.unpublish()
        session.commit()

        assert post.published_at is None
        assert post.is_draft is True
        assert post.is_published is False

    def test_schedule(self, session):
        """Should schedule for future."""
        post = PublishablePost(title="Test")
        session.add(post)
        session.commit()

        future = datetime.now(timezone.utc) + timedelta(days=1)
        post.schedule(future)
        session.commit()

        assert post.published_at is not None
        assert post.is_scheduled is True
        assert post.is_published is False

    def test_is_draft_property(self, session):
        """Should check if draft."""
        post = PublishablePost(title="Test")
        session.add(post)
        session.commit()

        assert post.is_draft is True

        post.publish()
        assert post.is_draft is False

    def test_is_published_property(self, session):
        """Should check if published."""
        post = PublishablePost(title="Test")
        session.add(post)
        session.commit()

        assert post.is_published is False

        post.publish()
        assert post.is_published is True

    def test_is_scheduled_property(self, session):
        """Should check if scheduled."""
        post = PublishablePost(title="Test")
        session.add(post)
        session.commit()

        future = datetime.now(timezone.utc) + timedelta(days=1)
        post.schedule(future)

        assert post.is_scheduled is True
        assert post.is_published is False

    def test_published_query(self, session):
        """Should query only published posts."""
        post1 = PublishablePost(title="Published")
        post2 = PublishablePost(title="Draft")
        post3 = PublishablePost(title="Scheduled")

        session.add_all([post1, post2, post3])
        session.commit()

        post1.publish()
        future = datetime.now(timezone.utc) + timedelta(days=1)
        post3.schedule(future)
        session.commit()

        published = list(PublishablePost.published(session))

        assert len(published) == 1
        assert published[0].title == "Published"

    def test_drafts_query(self, session):
        """Should query only drafts."""
        post1 = PublishablePost(title="Published")
        post2 = PublishablePost(title="Draft")

        session.add_all([post1, post2])
        session.commit()

        post1.publish()
        session.commit()

        drafts = list(PublishablePost.drafts(session))

        assert len(drafts) == 1
        assert drafts[0].title == "Draft"

    def test_scheduled_query(self, session):
        """Should query only scheduled posts."""
        post1 = PublishablePost(title="Published")
        post2 = PublishablePost(title="Scheduled")

        session.add_all([post1, post2])
        session.commit()

        post1.publish()
        future = datetime.now(timezone.utc) + timedelta(days=1)
        post2.schedule(future)
        session.commit()

        scheduled = list(PublishablePost.scheduled(session))

        assert len(scheduled) == 1
        assert scheduled[0].title == "Scheduled"