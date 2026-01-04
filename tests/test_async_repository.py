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
import pytest_asyncio
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

@pytest_asyncio.fixture(scope='function')
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


@pytest_asyncio.fixture(scope='function')
async def async_session(async_engine):
    """Create async session."""
    async_session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope='function')
async def user_repo(async_session):
    """Create user repository."""
    return AsyncRepository(User, async_session)


@pytest_asyncio.fixture(scope='function')
async def post_repo(async_session):
    """Create post repository."""
    return AsyncRepository(Post, async_session)


@pytest_asyncio.fixture(scope='function')
async def product_repo(async_session):
    """Create product repository."""
    return AsyncRepository(Product, async_session)


# ============================================================================
# Test CREATE Operations
# ============================================================================

class TestAsyncCreate:
    """Test async create operations."""

    @pytest.mark.asyncio
    async def test_create_basic(self, user_repo):
        """Should create a new record."""
        user = await user_repo.create({
            'name': 'John Doe',
            'email': 'john@example.com',
            'age': 30
        })

        assert user.id is not None
        assert user.name == 'John Doe'
        assert user.email == 'john@example.com'
        assert user.age == 30
        assert user.created_at is not None

    @pytest.mark.asyncio
    async def test_create_without_commit(self, user_repo):
        """Should create without committing."""
        user = await user_repo.create(
            {'name': 'Jane', 'email': 'jane@example.com'},
            commit=False
        )

        assert user.id is None  # Not committed yet

        await user_repo.commit()
        await user_repo.refresh(user)

        assert user.id is not None

    @pytest.mark.asyncio
    async def test_create_many(self, user_repo):
        """Should create multiple records."""
        users = await user_repo.create_many([
            {'name': 'User 1', 'email': 'user1@example.com'},
            {'name': 'User 2', 'email': 'user2@example.com'},
            {'name': 'User 3', 'email': 'user3@example.com'}
        ])

        assert len(users) == 3
        assert all(u.id is not None for u in users)
        assert users[0].name == 'User 1'
        assert users[1].name == 'User 2'
        assert users[2].name == 'User 3'

    @pytest.mark.asyncio
    async def test_create_many_without_commit(self, user_repo):
        """Should create many without committing."""
        users = await user_repo.create_many(
            [
                {'name': 'User A', 'email': 'a@example.com'},
                {'name': 'User B', 'email': 'b@example.com'}
            ],
            commit=False
        )

        assert all(u.id is None for u in users)

        await user_repo.commit()
        for user in users:
            await user_repo.refresh(user)

        assert all(u.id is not None for u in users)

    @pytest.mark.asyncio
    async def test_create_with_defaults(self, user_repo):
        """Should use default values."""
        user = await user_repo.create({
            'name': 'Test User',
            'email': 'test@example.com'
        })

        assert user.is_active is True  # Default value
        assert user.age is None  # Nullable


# ============================================================================
# Test READ Operations
# ============================================================================

class TestAsyncRead:
    """Test async read operations."""

    @pytest.mark.asyncio
    async def test_get(self, user_repo):
        """Should get record by ID."""
        user = await user_repo.create({
            'name': 'John',
            'email': 'john@example.com'
        })

        found = await user_repo.get(user.id)

        assert found is not None
        assert found.id == user.id
        assert found.name == 'John'

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, user_repo):
        """Should return None for nonexistent ID."""
        found = await user_repo.get(999)

        assert found is None

    @pytest.mark.asyncio
    async def test_get_or_404(self, user_repo):
        """Should get or raise error."""
        user = await user_repo.create({
            'name': 'John',
            'email': 'john@example.com'
        })

        found = await user_repo.get_or_404(user.id)

        assert found.id == user.id

    @pytest.mark.asyncio
    async def test_get_or_404_raises(self, user_repo):
        """Should raise error for nonexistent ID."""
        with pytest.raises(ValueError) as exc_info:
            await user_repo.get_or_404(999)

        assert 'not found' in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_get_all(self, user_repo):
        """Should get all records."""
        await user_repo.create_many([
            {'name': f'User {i}', 'email': f'user{i}@example.com'}
            for i in range(5)
        ])

        users = await user_repo.get_all()

        assert len(users) == 5

    @pytest.mark.asyncio
    async def test_get_all_with_limit(self, user_repo):
        """Should respect limit."""
        await user_repo.create_many([
            {'name': f'User {i}', 'email': f'user{i}@example.com'}
            for i in range(10)
        ])

        users = await user_repo.get_all(limit=3)

        assert len(users) == 3

    @pytest.mark.asyncio
    async def test_first(self, user_repo):
        """Should get first record."""
        await user_repo.create_many([
            {'name': 'Alice', 'email': 'alice@example.com', 'age': 25},
            {'name': 'Bob', 'email': 'bob@example.com', 'age': 30},
            {'name': 'Charlie', 'email': 'charlie@example.com', 'age': 35}
        ])

        first = await user_repo.first(_order_by='age')

        assert first.name == 'Alice'
        assert first.age == 25

    @pytest.mark.asyncio
    async def test_first_with_filter(self, user_repo):
        """Should get first matching filter."""
        await user_repo.create_many([
            {'name': 'Alice', 'email': 'alice@example.com', 'age': 25},
            {'name': 'Bob', 'email': 'bob@example.com', 'age': 30}
        ])

        first = await user_repo.first(age__gte=30)

        assert first.name == 'Bob'

    @pytest.mark.asyncio
    async def test_first_returns_none(self, user_repo):
        """Should return None if no matches."""
        first = await user_repo.first(name='Nonexistent')

        assert first is None

    @pytest.mark.asyncio
    async def test_exists(self, user_repo):
        """Should check if record exists."""
        await user_repo.create({
            'name': 'John',
            'email': 'john@example.com'
        })

        exists = await user_repo.exists(email='john@example.com')
        not_exists = await user_repo.exists(email='jane@example.com')

        assert exists is True
        assert not_exists is False

    @pytest.mark.asyncio
    async def test_count(self, user_repo):
        """Should count records."""
        await user_repo.create_many([
            {'name': f'User {i}', 'email': f'user{i}@example.com', 'age': 20 + i}
            for i in range(10)
        ])

        total = await user_repo.count()
        adults = await user_repo.count(age__gte=25)

        assert total == 10
        assert adults == 5  # ages 25-29
