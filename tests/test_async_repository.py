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


# ============================================================================
# Test FILTER Operations
# ============================================================================

class TestAsyncFilter:
    """Test async filtering."""

    @pytest.mark.asyncio
    async def test_filter_simple_equality(self, user_repo):
        """Should filter by equality."""
        await user_repo.create_many([
            {'name': 'Alice', 'email': 'alice@example.com', 'age': 25},
            {'name': 'Bob', 'email': 'bob@example.com', 'age': 30},
            {'name': 'Charlie', 'email': 'charlie@example.com', 'age': 25}
        ])

        results = await user_repo.filter(age=25)

        assert len(results) == 2
        assert all(u.age == 25 for u in results)

    @pytest.mark.asyncio
    async def test_filter_greater_than(self, user_repo):
        """Should filter with gt operator."""
        await user_repo.create_many([
            {'name': 'User 1', 'email': 'user1@example.com', 'age': 20},
            {'name': 'User 2', 'email': 'user2@example.com', 'age': 30},
            {'name': 'User 3', 'email': 'user3@example.com', 'age': 40}
        ])

        results = await user_repo.filter(age__gt=25)

        assert len(results) == 2
        assert all(u.age > 25 for u in results)

    @pytest.mark.asyncio
    async def test_filter_greater_than_or_equal(self, user_repo):
        """Should filter with gte operator."""
        await user_repo.create_many([
            {'name': 'User 1', 'email': 'user1@example.com', 'age': 20},
            {'name': 'User 2', 'email': 'user2@example.com', 'age': 30},
            {'name': 'User 3', 'email': 'user3@example.com', 'age': 40}
        ])

        results = await user_repo.filter(age__gte=30)

        assert len(results) == 2
        assert all(u.age >= 30 for u in results)

    @pytest.mark.asyncio
    async def test_filter_less_than(self, user_repo):
        """Should filter with lt operator."""
        await user_repo.create_many([
            {'name': 'User 1', 'email': 'user1@example.com', 'age': 20},
            {'name': 'User 2', 'email': 'user2@example.com', 'age': 30}
        ])

        results = await user_repo.filter(age__lt=25)

        assert len(results) == 1
        assert results[0].age == 20

    @pytest.mark.asyncio
    async def test_filter_in_operator(self, user_repo):
        """Should filter with in operator."""
        await user_repo.create_many([
            {'name': 'Alice', 'email': 'alice@example.com', 'age': 25},
            {'name': 'Bob', 'email': 'bob@example.com', 'age': 30},
            {'name': 'Charlie', 'email': 'charlie@example.com', 'age': 35}
        ])

        results = await user_repo.filter(age__in=[25, 35])

        assert len(results) == 2
        assert all(u.age in [25, 35] for u in results)

    @pytest.mark.asyncio
    async def test_filter_like_operator(self, user_repo):
        """Should filter with like operator."""
        await user_repo.create_many([
            {'name': 'Alice', 'email': 'alice@example.com'},
            {'name': 'Bob', 'email': 'bob@gmail.com'},
            {'name': 'Charlie', 'email': 'charlie@gmail.com'}
        ])

        results = await user_repo.filter(email__like='%gmail.com')

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_filter_ilike_operator(self, user_repo):
        """Should filter with case-insensitive like."""
        await user_repo.create_many([
            {'name': 'ALICE', 'email': 'alice@example.com'},
            {'name': 'alice', 'email': 'alice2@example.com'},
            {'name': 'Bob', 'email': 'bob@example.com'}
        ])

        results = await user_repo.filter(name__ilike='alice')

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_filter_startswith(self, user_repo):
        """Should filter with startswith."""
        await user_repo.create_many([
            {'name': 'John Doe', 'email': 'john@example.com'},
            {'name': 'Jane Doe', 'email': 'jane@example.com'},
            {'name': 'Bob Smith', 'email': 'bob@example.com'}
        ])

        results = await user_repo.filter(name__startswith='J')

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_filter_endswith(self, user_repo):
        """Should filter with endswith."""
        await user_repo.create_many([
            {'name': 'John Doe', 'email': 'john@example.com'},
            {'name': 'Jane Doe', 'email': 'jane@example.com'},
            {'name': 'Bob Smith', 'email': 'bob@example.com'}
        ])

        results = await user_repo.filter(name__endswith='Doe')

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_filter_contains(self, user_repo):
        """Should filter with contains."""
        await user_repo.create_many([
            {'name': 'Administrator', 'email': 'admin@example.com'},
            {'name': 'User Admin', 'email': 'useradmin@example.com'},
            {'name': 'Guest', 'email': 'guest@example.com'}
        ])

        results = await user_repo.filter(name__contains='Admin')

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_filter_multiple_conditions(self, user_repo):
        """Should filter with multiple conditions."""
        await user_repo.create_many([
            {'name': 'Alice', 'email': 'alice@example.com', 'age': 25, 'is_active': True},
            {'name': 'Bob', 'email': 'bob@example.com', 'age': 30, 'is_active': True},
            {'name': 'Charlie', 'email': 'charlie@example.com', 'age': 25, 'is_active': False}
        ])

        results = await user_repo.filter(age=25, is_active=True)

        assert len(results) == 1
        assert results[0].name == 'Alice'

    @pytest.mark.asyncio
    async def test_filter_with_limit(self, user_repo):
        """Should respect limit in filter."""
        await user_repo.create_many([
            {'name': f'User {i}', 'email': f'user{i}@example.com'}
            for i in range(10)
        ])

        results = await user_repo.filter(_limit=3)

        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_filter_with_offset(self, user_repo):
        """Should respect offset in filter."""
        await user_repo.create_many([
            {'name': f'User {i}', 'email': f'user{i}@example.com', 'age': i}
            for i in range(5)
        ])

        results = await user_repo.filter(_offset=2, _order_by='age')

        assert len(results) == 3
        assert results[0].age == 2

    @pytest.mark.asyncio
    async def test_filter_with_order_by_asc(self, user_repo):
        """Should order results ascending."""
        await user_repo.create_many([
            {'name': 'Charlie', 'email': 'charlie@example.com', 'age': 35},
            {'name': 'Alice', 'email': 'alice@example.com', 'age': 25},
            {'name': 'Bob', 'email': 'bob@example.com', 'age': 30}
        ])

        results = await user_repo.filter(_order_by='age')

        assert results[0].name == 'Alice'
        assert results[1].name == 'Bob'
        assert results[2].name == 'Charlie'

    @pytest.mark.asyncio
    async def test_filter_with_order_by_desc(self, user_repo):
        """Should order results descending."""
        await user_repo.create_many([
            {'name': 'Charlie', 'email': 'charlie@example.com', 'age': 35},
            {'name': 'Alice', 'email': 'alice@example.com', 'age': 25},
            {'name': 'Bob', 'email': 'bob@example.com', 'age': 30}
        ])

        results = await user_repo.filter(_order_by='-age')

        assert results[0].name == 'Charlie'
        assert results[1].name == 'Bob'
        assert results[2].name == 'Alice'

# ============================================================================
# Test UPDATE Operations
# ============================================================================

class TestAsyncUpdate:
    """Test async update operations."""

    @pytest.mark.asyncio
    async def test_update(self, user_repo):
        """Should update record."""
        user = await user_repo.create({
            'name': 'John',
            'email': 'john@example.com',
            'age': 25
        })

        updated = await user_repo.update(user.id, {
            'name': 'Jane',
            'age': 30
        })

        assert updated.name == 'Jane'
        assert updated.age == 30
        assert updated.email == 'john@example.com'  # Unchanged

    @pytest.mark.asyncio
    async def test_update_nonexistent(self, user_repo):
        """Should return None for nonexistent record."""
        updated = await user_repo.update(999, {'name': 'Test'})

        assert updated is None

    @pytest.mark.asyncio
    async def test_update_without_commit(self, user_repo):
        """Should update without committing."""
        user = await user_repo.create({
            'name': 'John',
            'email': 'john@example.com'
        })

        await user_repo.update(user.id, {'name': 'Jane'}, commit=False)

        # Not committed yet, rollback
        await user_repo.rollback()

        # Refresh and check
        await user_repo.refresh(user)
        assert user.name == 'John'  # Not changed

    @pytest.mark.asyncio
    async def test_update_many(self, user_repo):
        """Should update multiple records."""
        await user_repo.create_many([
            {'name': 'User 1', 'email': 'user1@example.com', 'is_active': True},
            {'name': 'User 2', 'email': 'user2@example.com', 'is_active': True},
            {'name': 'User 3', 'email': 'user3@example.com', 'is_active': False}
        ])

        count = await user_repo.update_many(
            filters={'is_active': True},
            data={'age': 25}
        )

        assert count == 2

        # Verify
        updated = await user_repo.filter(is_active=True)
        assert all(u.age == 25 for u in updated)


# ============================================================================
# Test DELETE Operations
# ============================================================================

class TestAsyncDelete:
    """Test async delete operations."""

    @pytest.mark.asyncio
    async def test_delete(self, user_repo):
        """Should delete record."""
        user = await user_repo.create({
            'name': 'John',
            'email': 'john@example.com'
        })

        deleted = await user_repo.delete(user.id)

        assert deleted is True

        # Verify deleted
        found = await user_repo.get(user.id)
        assert found is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, user_repo):
        """Should return False for nonexistent record."""
        deleted = await user_repo.delete(999)

        assert deleted is False

    @pytest.mark.asyncio
    async def test_soft_delete(self, post_repo):
        """Should soft delete if model supports it."""
        post = await post_repo.create({
            'title': 'Test Post',
            'content': 'Content',
            'user_id': 1
        })

        deleted = await post_repo.delete(post.id)

        assert deleted is True

        # Should not be found (soft deleted)
        found = await post_repo.get(post.id)
        assert found is None

    @pytest.mark.asyncio
    async def test_force_delete(self, post_repo):
        """Should force hard delete even with soft delete support."""
        post = await post_repo.create({
            'title': 'Test Post',
            'content': 'Content',
            'user_id': 1
        })

        deleted = await post_repo.delete(post.id, force=True)

        assert deleted is True

        # Verify hard deleted
        found = await post_repo.get(post.id)
        assert found is None

    @pytest.mark.asyncio
    async def test_delete_many(self, user_repo):
        """Should delete multiple records."""
        await user_repo.create_many([
            {'name': 'User 1', 'email': 'user1@example.com', 'is_active': False},
            {'name': 'User 2', 'email': 'user2@example.com', 'is_active': False},
            {'name': 'User 3', 'email': 'user3@example.com', 'is_active': True}
        ])

        count = await user_repo.delete_many({'is_active': False})

        assert count == 2

        # Verify
        remaining = await user_repo.count()
        assert remaining == 1


# ============================================================================
# Test PAGINATION
# ============================================================================

class TestAsyncPagination:
    """Test async pagination."""

    @pytest.mark.asyncio
    async def test_paginate_first_page(self, user_repo):
        """Should paginate first page."""
        await user_repo.create_many([
            {'name': f'User {i}', 'email': f'user{i}@example.com'}
            for i in range(25)
        ])

        items, meta = await user_repo.paginate(page=1, per_page=10)

        assert len(items) == 10
        assert meta['page'] == 1
        assert meta['per_page'] == 10
        assert meta['total'] == 25
        assert meta['total_pages'] == 3
        assert meta['has_next'] is True
        assert meta['has_prev'] is False

    @pytest.mark.asyncio
    async def test_paginate_middle_page(self, user_repo):
        """Should paginate middle page."""
        await user_repo.create_many([
            {'name': f'User {i}', 'email': f'user{i}@example.com'}
            for i in range(25)
        ])

        items, meta = await user_repo.paginate(page=2, per_page=10)

        assert len(items) == 10
        assert meta['page'] == 2
        assert meta['has_next'] is True
        assert meta['has_prev'] is True

    @pytest.mark.asyncio
    async def test_paginate_last_page(self, user_repo):
        """Should paginate last page."""
        await user_repo.create_many([
            {'name': f'User {i}', 'email': f'user{i}@example.com'}
            for i in range(25)
        ])

        items, meta = await user_repo.paginate(page=3, per_page=10)

        assert len(items) == 5  # Last page has 5 items
        assert meta['page'] == 3
        assert meta['has_next'] is False
        assert meta['has_prev'] is True

    @pytest.mark.asyncio
    async def test_paginate_with_filters(self, user_repo):
        """Should paginate with filters."""
        await user_repo.create_many([
            {'name': f'User {i}', 'email': f'user{i}@example.com', 'age': 20 + i}
            for i in range(20)
        ])

        items, meta = await user_repo.paginate(
            page=1,
            per_page=5,
            age__gte=25
        )

        assert len(items) == 5
        assert all(u.age >= 25 for u in items)
        assert meta['total'] == 15  # Only users with age >= 25

    @pytest.mark.asyncio
    async def test_paginate_with_ordering(self, user_repo):
        """Should paginate with ordering."""
        await user_repo.create_many([
            {'name': 'Charlie', 'email': 'charlie@example.com', 'age': 35},
            {'name': 'Alice', 'email': 'alice@example.com', 'age': 25},
            {'name': 'Bob', 'email': 'bob@example.com', 'age': 30}
        ])

        items, meta = await user_repo.paginate(
            page=1,
            per_page=10,
            _order_by='age'
        )

        assert items[0].name == 'Alice'
        assert items[1].name == 'Bob'
        assert items[2].name == 'Charlie'


# ============================================================================
# Test TRANSACTION Management
# ============================================================================

class TestAsyncTransactions:
    """Test async transaction management."""

    @pytest.mark.asyncio
    async def test_commit(self, user_repo):
        """Should commit transaction."""
        user = await user_repo.create(
            {'name': 'John', 'email': 'john@example.com'},
            commit=False
        )

        await user_repo.commit()
        await user_repo.refresh(user)

        assert user.id is not None

    @pytest.mark.asyncio
    async def test_rollback(self, user_repo):
        """Should rollback transaction."""
        user = await user_repo.create(
            {'name': 'John', 'email': 'john@example.com'},
            commit=False
        )

        await user_repo.rollback()

        # Count should be 0 after rollback
        count = await user_repo.count()
        assert count == 0

    @pytest.mark.asyncio
    async def test_flush(self, user_repo):
        """Should flush changes."""
        user = await user_repo.create(
            {'name': 'John', 'email': 'john@example.com'},
            commit=False
        )

        await user_repo.flush()

        # Should have ID after flush
        assert user.id is not None

        # But can still rollback
        await user_repo.rollback()
        count = await user_repo.count()
        assert count == 0

    @pytest.mark.asyncio
    async def test_refresh(self, user_repo):
        """Should refresh instance from database."""
        user = await user_repo.create({
            'name': 'John',
            'email': 'john@example.com'
        })

        # Manually change in DB (simulation)
        await user_repo.update(user.id, {'name': 'Jane'})

        # Refresh to get latest
        refreshed = await user_repo.refresh(user)

        assert refreshed.name == 'Jane'

