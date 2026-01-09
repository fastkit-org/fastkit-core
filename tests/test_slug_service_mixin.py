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


# ============================================================================
# Fixtures
# ============================================================================

@pytest_asyncio.fixture
async def async_engine():
    """Create in-memory async SQLite engine."""
    engine = create_async_engine('sqlite+aiosqlite:///:memory:', echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture
async def async_session(async_engine):
    """Create async database session."""
    async_session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def async_repository(async_session):
    """Create async repository."""
    return AsyncRepository(Article, async_session)


@pytest_asyncio.fixture
async def async_service(async_repository):
    """Create async service with slug mixin."""
    return ArticleAsyncService(async_repository)


@pytest.fixture
def mock_async_repository():
    """Create mock async repository."""
    mock_repo = AsyncMock()
    mock_repo.exists = AsyncMock(return_value=False)
    return mock_repo


@pytest.fixture
def mock_sync_repository():
    """Create mock sync repository."""
    mock_repo = MagicMock()
    mock_repo.exists = MagicMock(return_value=False)
    return mock_repo


