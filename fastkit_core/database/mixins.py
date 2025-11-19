"""
Useful mixins for models.

Provides common patterns:
- UUID primary keys
- Soft deletes
- Timestamps only (no ID)
- Slugs
- Publishing workflow
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column


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

        # Query only non-deleted
        active_posts = Post.query.filter(Post.deleted_at.is_(None)).all()
```
    """

    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None
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


class TimestampMixin:
    """
    Just timestamps, no primary key.

    Use when you want to define your own primary key
    but still want automatic timestamps.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )


class SlugMixin:
    """
    Automatic slug generation from title/name.

    Example:
```python
        class Post(Base, SlugMixin):
            __tablename__ = "posts"
            title: Mapped[str]

        post = Post(title="Hello World")
        post.generate_slug()  # slug = "hello-world"
```
    """

    slug: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )

    def generate_slug(self, source_field: str = 'title') -> str:
        """
        Generate slug from source field.

        Args:
            source_field: Field to generate slug from (default: 'title')

        Returns:
            Generated slug
        """
        import re

        source = getattr(self, source_field, '')

        # Convert to lowercase
        slug = source.lower()

        # Replace spaces and special chars with hyphens
        slug = re.sub(r'[^a-z0-9]+', '-', slug)

        # Remove leading/trailing hyphens
        slug = slug.strip('-')

        self.slug = slug
        return slug


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
        published = Article.query.filter(
            Article.is_published == True
        ).all()
```
    """

    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None
    )

    @property
    def is_published(self) -> bool:
        """Check if record is published."""
        if self.published_at is None:
            return False
        return self.published_at <= datetime.now(timezone.utc)

    @property
    def is_scheduled(self) -> bool:
        """Check if record is scheduled for future."""
        if self.published_at is None:
            return False
        return self.published_at > datetime.now(timezone.utc)

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
        """Schedule for future publication."""
        self.published_at = publish_at