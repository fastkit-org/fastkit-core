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


# ============================================================================
# Test Static Slugify Method
# ============================================================================

class TestSlugify:
    """Test static slugify method."""

    def test_basic_slugify(self):
        """Should convert basic text to slug."""
        slug = SlugServiceMixin.slugify("Hello World")

        assert slug == "hello-world"

    def test_slugify_with_special_chars(self):
        """Should remove special characters."""
        slug = SlugServiceMixin.slugify("Hello, World!")

        assert slug == "hello-world"

    def test_slugify_multiple_spaces(self):
        """Should replace multiple spaces with single separator."""
        slug = SlugServiceMixin.slugify("Hello    World")

        assert slug == "hello-world"

    def test_slugify_underscores(self):
        """Should replace underscores with separator."""
        slug = SlugServiceMixin.slugify("hello_world_test")

        assert slug == "hello-world-test"

    def test_slugify_custom_separator(self):
        """Should use custom separator."""
        slug = SlugServiceMixin.slugify("Hello World", separator='_')

        assert slug == "hello_world"

    def test_slugify_max_length(self):
        """Should limit slug length."""
        long_text = "a" * 300
        slug = SlugServiceMixin.slugify(long_text, max_length=50)

        assert len(slug) <= 50

    def test_slugify_empty_string(self):
        """Should handle empty string."""
        slug = SlugServiceMixin.slugify("")

        assert slug == ""

    def test_slugify_only_special_chars(self):
        """Should handle text with only special characters."""
        slug = SlugServiceMixin.slugify("!@#$%^&*()")

        assert slug == ""

    def test_slugify_leading_trailing_spaces(self):
        """Should remove leading and trailing spaces."""
        slug = SlugServiceMixin.slugify("  Hello World  ")

        assert slug == "hello-world"

    def test_slugify_numbers(self):
        """Should preserve numbers."""
        slug = SlugServiceMixin.slugify("Article 123")

        assert slug == "article-123"

