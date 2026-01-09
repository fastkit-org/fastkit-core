"""
Comprehensive tests for SlugServiceMixin.

Tests both async and sync slug generation with:
- Basic slug generation
- Uniqueness checking
- Auto-increment for duplicates
- Unicode handling
- Custom parameters
- Edge cases
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from fastkit_core.services import AsyncBaseCrudService, BaseCrudService, SlugServiceMixin
from fastkit_core.database import AsyncRepository, Repository


# ============================================================================
# Test Models & Schemas
# ============================================================================

class Base(DeclarativeBase):
    """Base for test models."""
    pass


class Article(Base):
    """Test article model with slug."""
    __tablename__ = 'test_articles'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(255), unique=True)


# ============================================================================
# Test Services
# ============================================================================

class ArticleAsyncService(SlugServiceMixin, AsyncBaseCrudService):
    """Async service with slug generation."""

    async def before_create(self, data: dict) -> dict:
        """Generate slug before creating."""
        if 'title' in data and not data.get('slug'):
            data['slug'] = await self.async_generate_slug(data['title'])
        return data

    async def before_update(self, id: int, data: dict) -> dict:
        """Regenerate slug if title changed."""
        if 'title' in data:
            data['slug'] = await self.async_generate_slug(
                data['title'],
                exclude_id=id
            )
        return data


class ArticleSyncService(SlugServiceMixin, BaseCrudService):
    """Sync service with slug generation."""

    def before_create(self, data: dict) -> dict:
        """Generate slug before creating."""
        if 'title' in data and not data.get('slug'):
            data['slug'] = self.generate_slug(data['title'])
        return data

    def before_update(self, id: int, data: dict) -> dict:
        """Regenerate slug if title changed."""
        if 'title' in data:
            data['slug'] = self.generate_slug(
                data['title'],
                exclude_id=id
            )
        return data

