"""
Comprehensive tests for AsyncRepository.

Tests:
- Async CRUD operations
- Filtering with operators
- Pagination
- Soft deletes
- Bulk operations
- Query helpers
- Transaction management
- Error handling

Target Coverage: 95%+
"""

import pytest
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, Integer, Numeric, DateTime, select
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from fastkit_core.database import Base, IntIdMixin, TimestampMixin, SoftDeleteMixin
from fastkit_core.database.async_repository import AsyncRepository, create_async_repository


# ============================================================================
# Test Models
# ============================================================================

class User(Base, IntIdMixin, TimestampMixin):
    """Test user model."""
    __tablename__ = 'async_repo_users'

    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(100), unique=True)
    age: Mapped[int] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)


class Post(Base, IntIdMixin, TimestampMixin, SoftDeleteMixin):
    """Test post model with soft delete."""
    __tablename__ = 'async_repo_posts'

    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(String(1000))
    views: Mapped[int] = mapped_column(Integer, default=0)
    user_id: Mapped[int] = mapped_column(Integer)


class Product(Base, IntIdMixin):
    """Test product model."""
    __tablename__ = 'async_repo_products'

    name: Mapped[str] = mapped_column(String(100))
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    stock: Mapped[int] = mapped_column(Integer, default=0)
    category: Mapped[str] = mapped_column(String(50))


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
async def async_engine():
    """Create async SQLite engine for testing."""
    engine = create_async_engine(
        'sqlite+aiosqlite:///:memory:',
        echo=False
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def async_session(async_engine):
    """Create async session."""
    async_session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session_maker() as session:
        yield session


@pytest.fixture
async def user_repo(async_session):
    """Create user repository."""
    return AsyncRepository(User, async_session)


@pytest.fixture
async def post_repo(async_session):
    """Create post repository."""
    return AsyncRepository(Post, async_session)


@pytest.fixture
async def product_repo(async_session):
    """Create product repository."""
    return AsyncRepository(Product, async_session)