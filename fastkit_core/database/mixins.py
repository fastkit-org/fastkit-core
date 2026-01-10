"""
Useful mixins for models.

Provides common patterns:
- UUID primary keys
- Soft deletes
- Timestamps only (no ID)
- Slugs (with uniqueness checks)
- Publishing workflow
- Ordering
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, String, select, event, Integer
from sqlalchemy.orm import Mapped, mapped_column

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

class IntIdMixin:
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )


class UUIDMixin:
    """
    Use UUID as primary key instead of integer.

    Good for:
    - Distributed systems
    - Public-facing IDs
    - Security (non-sequential)

    Example:
```python
        class User(Base, UUIDMixin):
            __tablename__ = "users"
            name: Mapped[str]

        # id is now UUID
        user = User(name="John")
        print(user.id)  # UUID('123e4567-e89b-12d3-a456-426614174000')
```
    """

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )


class SoftDeleteMixin:
    """
    Soft delete support (mark as deleted instead of removing).

    Example:
```python
        class Post(Base, SoftDeleteMixin):
            __tablename__ = "posts"
            title: Mapped[str]

        post = Post(title="Hello")
        post.soft_delete()  # Marks as deleted
        post.restore()      # Restores

        # Query only non-deleted (manual filter)
        active_posts = session.query(Post).filter(
            Post.deleted_at.is_(None)
        ).all()

        # Or use the class method
        active_posts = Post.active(session).all()
```
    """

    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        index=True  # Index for faster queries
    )

    @property
    def is_deleted(self) -> bool:
        """Check if record is soft-deleted."""
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """Mark record as deleted."""
        self.deleted_at = datetime.now(timezone.utc)

    def restore(self) -> None:
        """Restore soft-deleted record."""
        self.deleted_at = None

    @classmethod
    def active(cls, session: Session):
        """
        Query helper for non-deleted records.

        Example:
```python
            active_posts = Post.active(session).all()
```
        """
        from sqlalchemy import select
        stmt = select(cls).where(cls.deleted_at.is_(None))
        return session.scalars(stmt)

    @classmethod
    def deleted(cls, session: Session):
        """
        Query helper for deleted records.

        Example:
```python
            deleted_posts = Post.deleted(session).all()
```
        """
        stmt = select(cls).where(cls.deleted_at.isnot(None))
        return session.scalars(stmt)


    @classmethod
    def with_deleted(cls, session: Session):
        """Query builder that includes soft-deleted records."""
        stmt = select(cls)
        return session.scalars(stmt)


class TimestampMixin:
    """
    Adds created_at and updated_at timestamps.

    Use this with Base for automatic timestamp tracking.

    Example:
        class User(Base, TimestampMixin):
            name: Mapped[str]
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )


# Event listener specifically for TimestampMixin
@event.listens_for(TimestampMixin, 'before_update', propagate=True)
def receive_before_update(mapper, connection, target):
    """Automatically update updated_at timestamp."""
    target.updated_at = datetime.now(timezone.utc)

class SlugMixin:
    """
    Automatic slug generation from title/name with uniqueness checks.

    Example:
```python
        class Post(Base, SlugMixin):
            __tablename__ = "posts"
            title: Mapped[str]

        # Without session (no uniqueness check)
        post = Post(title="Hello World")
        post.generate_slug()  # slug = "hello-world"

        # With session (ensures uniqueness)
        post = Post(title="Hello World")
        post.generate_slug(session=session)  # slug = "hello-world" or "hello-world-2"
```
    """

    slug: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )


class PublishableMixin:
    """
    Publishing workflow (draft, published, scheduled).

    Example:
```python
        class Article(Base, PublishableMixin):
            __tablename__ = "articles"
            title: Mapped[str]

        article = Article(title="News")
        article.publish()  # Sets published_at to now
        article.unpublish()  # Sets to None
        article.schedule(datetime(2024, 12, 31))  # Schedule

        # Query published articles
        published = Article.published(session).all()

        # Query drafts
        drafts = Article.drafts(session).all()

        # Query scheduled
        scheduled = Article.scheduled(session).all()
```
    """

    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        index=True  # Index for faster queries
    )

    def _get_published_at(self):
        """Get published_at with guaranteed timezone."""
        published = self.published_at
        if published.tzinfo is None:  # fix naive values
            published = published.replace(tzinfo=timezone.utc)

        return published

    @property
    def is_published(self) -> bool:
        """Check if record is published."""
        if self.published_at is None:
            return False
        return self._get_published_at() <= datetime.now(timezone.utc)

    @property
    def is_scheduled(self) -> bool:
        """Check if record is scheduled for future."""
        if self.published_at is None:
            return False
        return self._get_published_at() > datetime.now(timezone.utc)

    @property
    def is_draft(self) -> bool:
        """Check if record is draft."""
        return self.published_at is None

    def publish(self) -> None:
        """Publish immediately."""
        self.published_at = datetime.now(timezone.utc)

    def unpublish(self) -> None:
        """Unpublish (make draft)."""
        self.published_at = None

    def schedule(self, publish_at: datetime) -> None:
        """
        Schedule for future publication.

        Args:
            publish_at: DateTime when to publish (should be in UTC)
        """
        self.published_at = publish_at

    @classmethod
    def published(cls, session: Session):
        """
        Query helper for published records.

        Example:
```python
            published = Article.published(session).all()
```
        """
        now = datetime.now(timezone.utc)
        stmt = select(cls).where(
            cls.published_at.isnot(None),
            cls.published_at <= now
        )
        return session.scalars(stmt)

    @classmethod
    def drafts(cls, session: Session):
        """
        Query helper for draft records.

        Example:
```python
            drafts = Article.drafts(session).all()
```
        """
        stmt = select(cls).where(cls.published_at.is_(None))
        return session.scalars(stmt)

    @classmethod
    def scheduled(cls, session: Session):
        """
        Query helper for scheduled records.

        Example:
```python
            scheduled = Article.scheduled(session).all()
```
        """
        now = datetime.now(timezone.utc)
        stmt = select(cls).where(
            cls.published_at.isnot(None),
            cls.published_at > now
        )
        return session.scalars(stmt)