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


# ============================================================================
# Test Async Generate Slug
# ============================================================================

class TestAsyncGenerateSlug:
    """Test async slug generation."""

    @pytest.mark.asyncio
    async def test_generate_basic_slug(self, mock_async_repository):
        """Should generate basic slug."""
        service = ArticleAsyncService(mock_async_repository)

        slug = await service.async_generate_slug("Hello World")

        assert slug == "hello-world"
        mock_async_repository.exists.assert_called_once_with(slug="hello-world")

    @pytest.mark.asyncio
    async def test_generate_unique_slug_with_increment(self, mock_async_repository):
        """Should append number for duplicate slugs."""
        # First check returns True (exists), second returns False
        mock_async_repository.exists = AsyncMock(side_effect=[True, False])

        service = ArticleAsyncService(mock_async_repository)
        slug = await service.async_generate_slug("Hello World")

        assert slug == "hello-world-2"
        assert mock_async_repository.exists.call_count == 2

    @pytest.mark.asyncio
    async def test_generate_slug_multiple_duplicates(self, mock_async_repository):
        """Should keep incrementing until unique."""
        # First 3 checks return True, 4th returns False
        mock_async_repository.exists = AsyncMock(
            side_effect=[True, True, True, False]
        )

        service = ArticleAsyncService(mock_async_repository)
        slug = await service.async_generate_slug("Hello World")

        assert slug == "hello-world-4"
        assert mock_async_repository.exists.call_count == 4

    @pytest.mark.asyncio
    async def test_generate_slug_with_exclude_id(self, mock_async_repository):
        """Should exclude current record from uniqueness check."""
        service = ArticleAsyncService(mock_async_repository)

        slug = await service.async_generate_slug(
            "Hello World",
            exclude_id=5
        )

        assert slug == "hello-world"
        mock_async_repository.exists.assert_called_once_with(
            slug="hello-world",
            id__ne=5
        )

    @pytest.mark.asyncio
    async def test_generate_slug_custom_field(self, mock_async_repository):
        """Should use custom slug field name."""
        service = ArticleAsyncService(mock_async_repository)

        slug = await service.async_generate_slug(
            "Hello World",
            slug_field='url_slug'
        )

        assert slug == "hello-world"
        mock_async_repository.exists.assert_called_once_with(url_slug="hello-world")

    @pytest.mark.asyncio
    async def test_generate_slug_custom_separator(self, mock_async_repository):
        """Should use custom separator."""
        service = ArticleAsyncService(mock_async_repository)

        slug = await service.async_generate_slug(
            "Hello World",
            separator='_'
        )

        assert slug == "hello_world"

    @pytest.mark.asyncio
    async def test_generate_slug_max_length(self, mock_async_repository):
        """Should respect max length."""
        service = ArticleAsyncService(mock_async_repository)

        long_text = "a" * 300
        slug = await service.async_generate_slug(long_text, max_length=50)

        assert len(slug) <= 50

    @pytest.mark.asyncio
    async def test_generate_slug_empty_text_raises_error(self, mock_async_repository):
        """Should raise error for empty text."""
        service = ArticleAsyncService(mock_async_repository)

        with pytest.raises(ValueError) as exc_info:
            await service.async_generate_slug("")

        assert "Cannot generate slug from empty text" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_slug_without_repository_raises_error(self):
        """Should raise error if service has no repository."""
        service = ArticleAsyncService(None)
        service.repository = None  # Remove repository

        with pytest.raises(AttributeError) as exc_info:
            await service.async_generate_slug("Hello")

        assert "must have 'repository' attribute" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_slug_safety_limit(self, mock_async_repository):
        """Should add UUID after 1000 attempts."""
        # Always return True to trigger safety limit
        mock_async_repository.exists = AsyncMock(return_value=True)

        service = ArticleAsyncService(mock_async_repository)
        slug = await service.async_generate_slug("Hello")

        # Should have UUID suffix
        assert slug.startswith("hello-")
        assert len(slug.split('-')) == 2  # "hello-{uuid}"
        assert len(slug.split('-')[1]) == 8  # UUID is 8 chars


# ============================================================================
# Test Sync Generate Slug
# ============================================================================

class TestSyncGenerateSlug:
    """Test sync slug generation."""

    def test_generate_basic_slug(self, mock_sync_repository):
        """Should generate basic slug."""
        service = ArticleSyncService(mock_sync_repository)

        slug = service.generate_slug("Hello World")

        assert slug == "hello-world"
        mock_sync_repository.exists.assert_called_once_with(slug="hello-world")

    def test_generate_unique_slug_with_increment(self, mock_sync_repository):
        """Should append number for duplicate slugs."""
        mock_sync_repository.exists = MagicMock(side_effect=[True, False])

        service = ArticleSyncService(mock_sync_repository)
        slug = service.generate_slug("Hello World")

        assert slug == "hello-world-2"
        assert mock_sync_repository.exists.call_count == 2

    def test_generate_slug_with_exclude_id(self, mock_sync_repository):
        """Should exclude current record."""
        service = ArticleSyncService(mock_sync_repository)

        slug = service.generate_slug("Hello World", exclude_id=5)

        mock_sync_repository.exists.assert_called_once_with(
            slug="hello-world",
            id__ne=5
        )

    def test_generate_slug_custom_field(self, mock_sync_repository):
        """Should use custom slug field."""
        service = ArticleSyncService(mock_sync_repository)

        slug = service.generate_slug("Hello World", slug_field='url_slug')

        mock_sync_repository.exists.assert_called_once_with(url_slug="hello-world")


# ============================================================================
# Test Integration with Real Database (Async)
# ============================================================================

class TestAsyncIntegration:
    """Test async service integration with real database."""

    @pytest.mark.asyncio
    async def test_create_article_with_slug(self, async_service):
        """Should create article with auto-generated slug."""
        # Mock create to avoid full implementation
        async_service.repository.create = AsyncMock(
            return_value=Article(id=1, title="Hello World", slug="hello-world")
        )
        async_service.repository.exists = AsyncMock(return_value=False)

        data = {"title": "Hello World"}
        result_data = await async_service.before_create(data)

        assert 'slug' in result_data
        assert result_data['slug'] == "hello-world"

    @pytest.mark.asyncio
    async def test_create_duplicate_title(self, async_service):
        """Should generate unique slug for duplicate titles."""
        # First slug exists
        async_service.repository.exists = AsyncMock(side_effect=[True, False])

        data = {"title": "Hello World"}
        result_data = await async_service.before_create(data)

        assert result_data['slug'] == "hello-world-2"

    @pytest.mark.asyncio
    async def test_update_article_regenerates_slug(self, async_service):
        """Should regenerate slug on update."""
        async_service.repository.exists = AsyncMock(return_value=False)

        data = {"title": "New Title"}
        result_data = await async_service.before_update(5, data)

        assert result_data['slug'] == "new-title"
        async_service.repository.exists.assert_called_once_with(
            slug="new-title",
            id__ne=5
        )

    @pytest.mark.asyncio
    async def test_manual_slug_override(self, async_service):
        """Should allow manual slug override."""
        data = {"title": "Hello World", "slug": "custom-slug"}
        result_data = await async_service.before_create(data)

        # Should keep manual slug
        assert result_data['slug'] == "custom-slug"


# ============================================================================
# Test Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_slug_with_only_numbers(self, mock_async_repository):
        """Should handle text with only numbers."""
        service = ArticleAsyncService(mock_async_repository)

        slug = await service.async_generate_slug("12345")

        assert slug == "12345"

    @pytest.mark.asyncio
    async def test_slug_with_mixed_case(self, mock_async_repository):
        """Should convert to lowercase."""
        service = ArticleAsyncService(mock_async_repository)

        slug = await service.async_generate_slug("Hello WORLD Test")

        assert slug == "hello-world-test"

    @pytest.mark.asyncio
    async def test_slug_with_emojis(self, mock_async_repository):
        """Should remove emojis."""
        service = ArticleAsyncService(mock_async_repository)

        slug = await service.async_generate_slug("Hello 😀 World 🎉")

        assert slug == "hello-world"

    @pytest.mark.asyncio
    async def test_very_long_slug(self, mock_async_repository):
        """Should handle very long text."""
        service = ArticleAsyncService(mock_async_repository)

        long_text = "word " * 100  # 500 chars
        slug = await service.async_generate_slug(long_text, max_length=100)

        assert len(slug) <= 100

    @pytest.mark.asyncio
    async def test_slug_with_multiple_separators(self, mock_async_repository):
        """Should collapse multiple separators."""
        service = ArticleAsyncService(mock_async_repository)

        slug = await service.async_generate_slug("Hello---World___Test")

        assert slug == "hello-world-test"

    def test_sync_slug_special_characters(self, mock_sync_repository):
        """Should handle special characters in sync version."""
        service = ArticleSyncService(mock_sync_repository)

        slug = service.generate_slug("C++ Programming & Design")

        assert slug == "c-programming-design"


# ============================================================================
# Test Real-World Scenarios
# ============================================================================

class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    @pytest.mark.asyncio
    async def test_blog_post_slug(self, mock_async_repository):
        """Should generate slug for blog post title."""
        service = ArticleAsyncService(mock_async_repository)

        slug = await service.async_generate_slug(
            "10 Tips for Better Python Code in 2024"
        )

        assert slug == "10-tips-for-better-python-code-in-2024"

    @pytest.mark.asyncio
    async def test_product_slug_with_category(self, mock_async_repository):
        """Should generate slug with category prefix."""
        service = ArticleAsyncService(mock_async_repository)

        slug = await service.async_generate_slug("Electronics Laptop Pro 15 inch")

        assert slug == "electronics-laptop-pro-15-inch"

    @pytest.mark.asyncio
    async def test_article_series_slugs(self, mock_async_repository):
        """Should generate unique slugs for article series."""
        # Simulate existing articles in series
        mock_async_repository.exists = AsyncMock(
            side_effect=[
                True,  # Part 1 exists
                True,  # Part 2 exists
                False  # Part 3 is unique
            ]
        )

        service = ArticleAsyncService(mock_async_repository)
        slug = await service.async_generate_slug("Python Tutorial Part 1")

        assert slug == "python-tutorial-part-1-3"

    @pytest.mark.asyncio
    async def test_multilingual_slug(self, mock_async_repository):
        """Should handle multilingual content."""
        service = ArticleAsyncService(mock_async_repository)

        slug = await service.async_generate_slug("Učenje Python programiranja")

        assert slug == "ucenje-python-programiranja"
