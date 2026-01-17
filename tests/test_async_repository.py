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
from sqlalchemy import String, Integer, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from fastkit_core.database import Base, IntIdMixin, TimestampMixin, SoftDeleteMixin
from fastkit_core.database.async_repository import AsyncRepository, create_async_repository


# ============================================================================
# Test Models
# ============================================================================

class AsyncUser(Base, IntIdMixin, TimestampMixin):
    """Test user model for async repository tests."""
    __tablename__ = 'async_repo_users'

    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(100), unique=True)
    age: Mapped[int] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)

    # Relationships
    posts: Mapped[list["AsyncPost"]] = relationship(
        "AsyncPost",
        foreign_keys="AsyncPost.user_id",
        viewonly=True
    )


class AsyncPost(Base, IntIdMixin, TimestampMixin, SoftDeleteMixin):
    """Test post model with soft delete for async repository tests."""
    __tablename__ = 'async_repo_posts'

    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(String(1000))
    views: Mapped[int] = mapped_column(Integer, default=0)
    user_id: Mapped[int] = mapped_column(ForeignKey('async_repo_users.id'))

    # Relationships
    user: Mapped["AsyncUser"] = relationship(
        "AsyncUser",
        foreign_keys=[user_id],
        viewonly=True
    )


class AsyncProduct(Base, IntIdMixin):
    """Test product model for async repository tests."""
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
    return AsyncRepository(AsyncUser, async_session)


@pytest_asyncio.fixture(scope='function')
async def post_repo(async_session):
    """Create post repository."""
    return AsyncRepository(AsyncPost, async_session)


@pytest_asyncio.fixture(scope='function')
async def product_repo(async_session):
    """Create product repository."""
    return AsyncRepository(AsyncProduct, async_session)


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
            {'name': 'AsyncUser 1', 'email': 'user1@example.com'},
            {'name': 'AsyncUser 2', 'email': 'user2@example.com'},
            {'name': 'AsyncUser 3', 'email': 'user3@example.com'}
        ])

        assert len(users) == 3
        assert all(u.id is not None for u in users)
        assert users[0].name == 'AsyncUser 1'
        assert users[1].name == 'AsyncUser 2'
        assert users[2].name == 'AsyncUser 3'

    @pytest.mark.asyncio
    async def test_create_many_without_commit(self, user_repo):
        """Should create many without committing."""
        users = await user_repo.create_many(
            [
                {'name': 'AsyncUser A', 'email': 'a@example.com'},
                {'name': 'AsyncUser B', 'email': 'b@example.com'}
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
            'name': 'Test AsyncUser',
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
            {'name': f'AsyncUser {i}', 'email': f'user{i}@example.com'}
            for i in range(5)
        ])

        users = await user_repo.get_all()

        assert len(users) == 5

    @pytest.mark.asyncio
    async def test_get_all_with_limit(self, user_repo):
        """Should respect limit."""
        await user_repo.create_many([
            {'name': f'AsyncUser {i}', 'email': f'user{i}@example.com'}
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
            {'name': f'AsyncUser {i}', 'email': f'user{i}@example.com', 'age': 20 + i}
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
            {'name': 'AsyncUser 1', 'email': 'user1@example.com', 'age': 20},
            {'name': 'AsyncUser 2', 'email': 'user2@example.com', 'age': 30},
            {'name': 'AsyncUser 3', 'email': 'user3@example.com', 'age': 40}
        ])

        results = await user_repo.filter(age__gt=25)

        assert len(results) == 2
        assert all(u.age > 25 for u in results)

    @pytest.mark.asyncio
    async def test_filter_greater_than_or_equal(self, user_repo):
        """Should filter with gte operator."""
        await user_repo.create_many([
            {'name': 'AsyncUser 1', 'email': 'user1@example.com', 'age': 20},
            {'name': 'AsyncUser 2', 'email': 'user2@example.com', 'age': 30},
            {'name': 'AsyncUser 3', 'email': 'user3@example.com', 'age': 40}
        ])

        results = await user_repo.filter(age__gte=30)

        assert len(results) == 2
        assert all(u.age >= 30 for u in results)

    @pytest.mark.asyncio
    async def test_filter_less_than(self, user_repo):
        """Should filter with lt operator."""
        await user_repo.create_many([
            {'name': 'AsyncUser 1', 'email': 'user1@example.com', 'age': 20},
            {'name': 'AsyncUser 2', 'email': 'user2@example.com', 'age': 30}
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
            {'name': 'AsyncUser Admin', 'email': 'useradmin@example.com'},
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
            {'name': f'AsyncUser {i}', 'email': f'user{i}@example.com'}
            for i in range(10)
        ])

        results = await user_repo.filter(_limit=3)

        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_filter_with_offset(self, user_repo):
        """Should respect offset in filter."""
        await user_repo.create_many([
            {'name': f'AsyncUser {i}', 'email': f'user{i}@example.com', 'age': i}
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
            {'name': 'AsyncUser 1', 'email': 'user1@example.com', 'is_active': True},
            {'name': 'AsyncUser 2', 'email': 'user2@example.com', 'is_active': True},
            {'name': 'AsyncUser 3', 'email': 'user3@example.com', 'is_active': False}
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
            'title': 'Test AsyncPost',
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
            'title': 'Test AsyncPost',
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
            {'name': 'AsyncUser 1', 'email': 'user1@example.com', 'is_active': False},
            {'name': 'AsyncUser 2', 'email': 'user2@example.com', 'is_active': False},
            {'name': 'AsyncUser 3', 'email': 'user3@example.com', 'is_active': True}
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
            {'name': f'AsyncUser {i}', 'email': f'user{i}@example.com'}
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
            {'name': f'AsyncUser {i}', 'email': f'user{i}@example.com'}
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
            {'name': f'AsyncUser {i}', 'email': f'user{i}@example.com'}
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
            {'name': f'AsyncUser {i}', 'email': f'user{i}@example.com', 'age': 20 + i}
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


# ============================================================================
# Test ERROR Handling
# ============================================================================

class TestAsyncErrorHandling:
    """Test async error handling."""

    @pytest.mark.asyncio
    async def test_invalid_field_raises_error(self, user_repo):
        """Should raise error for invalid field."""
        with pytest.raises(ValueError) as exc_info:
            await user_repo.filter(nonexistent_field='value')

        assert 'does not exist' in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_invalid_operator_raises_error(self, user_repo):
        """Should raise error for invalid operator."""
        with pytest.raises(ValueError) as exc_info:
            await user_repo.filter(name__invalid_op='value')

        assert 'unknown operator' in str(exc_info.value).lower()


# ============================================================================
# Test FACTORY Function
# ============================================================================

class TestAsyncRepositoryFactory:
    """Test async repository factory."""

    @pytest.mark.asyncio
    async def test_create_async_repository(self, async_session):
        """Should create repository using factory."""
        repo = create_async_repository(AsyncUser, async_session)

        assert isinstance(repo, AsyncRepository)
        assert repo.model == AsyncUser
        assert repo.session == async_session

    @pytest.mark.asyncio
    async def test_factory_repository_works(self, async_session):
        """Should work same as direct instantiation."""
        repo = create_async_repository(AsyncUser, async_session)

        user = await repo.create({
            'name': 'Test',
            'email': 'test@example.com'
        })

        assert user.id is not None
        assert user.name == 'Test'


# ============================================================================
# Test EDGE Cases
# ============================================================================

class TestAsyncEdgeCases:
    """Test edge cases."""

    @pytest.mark.asyncio
    async def test_empty_result_set(self, user_repo):
        """Should handle empty results."""
        results = await user_repo.filter(name='Nonexistent')

        assert results == []
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_paginate_empty_results(self, user_repo):
        """Should handle pagination with no results."""
        items, meta = await user_repo.paginate(page=1, per_page=10)

        assert items == []
        assert meta['total'] == 0
        assert meta['total_pages'] == 0

    @pytest.mark.asyncio
    async def test_update_with_empty_dict(self, user_repo):
        """Should handle update with empty dict."""
        user = await user_repo.create({
            'name': 'John',
            'email': 'john@example.com'
        })

        updated = await user_repo.update(user.id, {})

        assert updated.name == 'John'  # Unchanged

    @pytest.mark.asyncio
    async def test_filter_with_none_value(self, user_repo):
        """Should handle None in filters."""
        await user_repo.create({
            'name': 'John',
            'email': 'john@example.com',
            'age': None
        })

        # This should work without errors
        results = await user_repo.filter(age=None)
        assert len(results) >= 0


# ============================================================================
# Test SPECIAL Scenarios
# ============================================================================

class TestAsyncSpecialScenarios:
    """Test special real-world scenarios."""

    @pytest.mark.asyncio
    async def test_complex_filtering_scenario(self, product_repo):
        """Should handle complex filtering (e-commerce scenario)."""
        # Create products
        await product_repo.create_many([
            {'name': 'Laptop', 'price': Decimal('999.99'), 'stock': 10, 'category': 'Electronics'},
            {'name': 'Phone', 'price': Decimal('599.99'), 'stock': 5, 'category': 'Electronics'},
            {'name': 'Desk', 'price': Decimal('299.99'), 'stock': 0, 'category': 'Furniture'},
            {'name': 'Chair', 'price': Decimal('149.99'), 'stock': 20, 'category': 'Furniture'},
            {'name': 'Book', 'price': Decimal('29.99'), 'stock': 100, 'category': 'Books'}
        ])

        # Find available electronics under $1000
        results = await product_repo.filter(
            category='Electronics',
            price__lt=Decimal('1000'),
            stock__gt=0,
            _order_by='price'
        )

        assert len(results) == 2
        assert results[0].name == 'Phone'
        assert results[1].name == 'Laptop'

    @pytest.mark.asyncio
    async def test_search_functionality(self, user_repo):
        """Should implement search functionality."""
        await user_repo.create_many([
            {'name': 'John Doe', 'email': 'john.doe@example.com'},
            {'name': 'Jane Doe', 'email': 'jane.doe@example.com'},
            {'name': 'Bob Smith', 'email': 'bob.smith@gmail.com'},
            {'name': 'Alice Johnson', 'email': 'alice.johnson@gmail.com'}
        ])

        # Search for "doe" in name or email
        doe_results = await user_repo.filter(name__ilike='%doe%')
        gmail_results = await user_repo.filter(email__endswith='gmail.com')

        assert len(doe_results) == 2
        assert len(gmail_results) == 2

    @pytest.mark.asyncio
    async def test_bulk_operations_performance(self, user_repo):
        """Should handle bulk operations efficiently."""
        import time

        # Create 100 users in bulk
        start = time.time()
        users = await user_repo.create_many([
            {'name': f'AsyncUser {i}', 'email': f'user{i}@example.com'}
            for i in range(100)
        ])
        bulk_time = time.time() - start

        assert len(users) == 100

        # Bulk create should be reasonably fast (< 2 seconds)
        assert bulk_time < 2.0

    @pytest.mark.asyncio
    async def test_concurrent_reads(self, user_repo):
        """Should handle concurrent reads."""
        import asyncio

        # Create test data
        await user_repo.create_many([
            {'name': f'AsyncUser {i}', 'email': f'user{i}@example.com'}
            for i in range(10)
        ])

        # Simulate concurrent reads
        async def read_users():
            return await user_repo.get_all()

        results = await asyncio.gather(*[read_users() for _ in range(10)])

        # All should return same count
        assert all(len(r) == 10 for r in results)

    @pytest.mark.asyncio
    async def test_soft_delete_filtering(self, post_repo):
        """Should exclude soft-deleted records by default."""
        # Create posts
        posts = await post_repo.create_many([
            {'title': f'AsyncPost {i}', 'content': 'Content', 'user_id': 1}
            for i in range(5)
        ])

        # Soft delete some
        await post_repo.delete(posts[0].id)
        await post_repo.delete(posts[2].id)

        # Should only return non-deleted
        all_posts = await post_repo.get_all()
        assert len(all_posts) == 3

        # Count should also exclude deleted
        count = await post_repo.count()
        assert count == 3

    @pytest.mark.asyncio
    async def test_decimal_precision(self, product_repo):
        """Should handle decimal precision correctly."""
        product = await product_repo.create({
            'name': 'Test AsyncProduct',
            'price': Decimal('19.99'),
            'stock': 10,
            'category': 'Test'
        })

        assert product.price == Decimal('19.99')
        assert isinstance(product.price, Decimal)

    @pytest.mark.asyncio
    async def test_timestamp_auto_population(self, user_repo):
        """Should auto-populate timestamps."""
        user = await user_repo.create({
            'name': 'John',
            'email': 'john@example.com'
        })

        assert user.created_at is not None
        assert user.updated_at is not None
        assert isinstance(user.created_at, datetime)
        assert isinstance(user.updated_at, datetime)

    @pytest.mark.asyncio
    async def test_filtering_with_between(self, product_repo):
        """Should filter with between operator."""
        await product_repo.create_many([
            {'name': 'AsyncProduct 1', 'price': Decimal('10.00'), 'stock': 5, 'category': 'A'},
            {'name': 'AsyncProduct 2', 'price': Decimal('50.00'), 'stock': 5, 'category': 'A'},
            {'name': 'AsyncProduct 3', 'price': Decimal('100.00'), 'stock': 5, 'category': 'A'},
            {'name': 'AsyncProduct 4', 'price': Decimal('150.00'), 'stock': 5, 'category': 'A'}
        ])

        results = await product_repo.filter(
            price__between=(Decimal('40.00'), Decimal('120.00'))
        )

        assert len(results) == 2
        assert all(Decimal('40.00') <= p.price <= Decimal('120.00') for p in results)

    @pytest.mark.asyncio
    async def test_pagination_boundary_cases(self, user_repo):
        """Should handle pagination boundary cases."""
        await user_repo.create_many([
            {'name': f'AsyncUser {i}', 'email': f'user{i}@example.com'}
            for i in range(3)
        ])

        # Page beyond total
        items, meta = await user_repo.paginate(page=10, per_page=10)
        assert items == []
        assert meta['total_pages'] == 1

        # Per page larger than total
        items, meta = await user_repo.paginate(page=1, per_page=100)
        assert len(items) == 3
        assert meta['total_pages'] == 1


# ============================================================================
# Test REPOSITORY Methods
# ============================================================================

class TestAsyncRepositoryMethods:
    """Test repository helper methods."""

    @pytest.mark.asyncio
    async def test_has_soft_delete(self, user_repo, post_repo):
        """Should detect soft delete support."""
        assert user_repo._has_soft_delete() is False
        assert post_repo._has_soft_delete() is True

    @pytest.mark.asyncio
    async def test_query_builder(self, user_repo):
        """Should provide query builder."""
        query = user_repo.query()

        assert query is not None
        # Query should be a select statement
        assert 'SELECT' in str(query).upper()

    @pytest.mark.asyncio
    async def test_parse_field_operator_valid(self, user_repo):
        """Should parse valid field operators."""
        conditions = []

        # Should not raise error
        user_repo._parse_field_operator('name__eq', 'test', conditions)
        user_repo._parse_field_operator('age__gte', 18, conditions)

        assert len(conditions) == 2

    @pytest.mark.asyncio
    async def test_parse_field_operator_invalid_field(self, user_repo):
        """Should raise error for invalid field."""
        conditions = []

        with pytest.raises(ValueError) as exc_info:
            user_repo._parse_field_operator('invalid_field__eq', 'test', conditions)

        assert 'does not exist' in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_parse_field_operator_invalid_operator(self, user_repo):
        """Should raise error for invalid operator."""
        conditions = []

        with pytest.raises(ValueError) as exc_info:
            user_repo._parse_field_operator('name__bad_op', 'test', conditions)

        assert 'unknown operator' in str(exc_info.value).lower()


# ============================================================================
# Test INTEGRATION with FastAPI
# ============================================================================

class TestAsyncFastAPIIntegration:
    """Test integration patterns with FastAPI."""

    @pytest.mark.asyncio
    async def test_repository_in_service_layer(self, async_session):
        """Should work in service layer pattern."""

        class UserService:
            def __init__(self, db: AsyncSession):
                self.repo = AsyncRepository(AsyncUser, db)

            async def create_user(self, name: str, email: str):
                return await self.repo.create({'name': name, 'email': email})

            async def get_active_users(self):
                return await self.repo.filter(is_active=True)

            async def search_users(self, query: str):
                return await self.repo.filter(name__ilike=f'%{query}%')

        service = UserService(async_session)

        # Create user
        user = await service.create_user('John Doe', 'john@example.com')
        assert user.id is not None

        # Get active users
        active = await service.get_active_users()
        assert len(active) == 1

        # Search
        results = await service.search_users('john')
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_repository_with_dto_pattern(self, user_repo):
        """Should work with DTO/Pydantic models."""
        from typing import Optional

        # Simulate Pydantic model
        class UserCreate:
            def __init__(self, name: str, email: str, age: Optional[int] = None):
                self.name = name
                self.email = email
                self.age = age

            def dict(self):
                return {
                    'name': self.name,
                    'email': self.email,
                    'age': self.age
                }

        # Create from DTO
        dto = UserCreate(name='John', email='john@example.com', age=30)
        user = await user_repo.create(dto.dict())

        assert user.name == 'John'
        assert user.age == 30


# ============================================================================
# Test Eager Loading (Relationship Loading)
# ============================================================================

class TestAsyncEagerLoading:
    """Test eager loading functionality to prevent N+1 queries."""

    @pytest.mark.asyncio
    async def test_get_with_load_relations_single(self, user_repo, post_repo):
        """Should load single relationship with get()."""
        # Create user with posts
        user = await user_repo.create({
            'name': 'John Doe',
            'email': 'john@example.com'
        })

        await post_repo.create({
            'title': 'First AsyncPost',
            'content': 'Content here',
            'user_id': user.id
        })
        await post_repo.create({
            'title': 'Second AsyncPost',
            'content': 'More content',
            'user_id': user.id
        })

        # Get user with posts loaded
        loaded_user = await user_repo.get(user.id, load_relations=['posts'])

        assert loaded_user is not None
        assert len(loaded_user.posts) == 2
        assert loaded_user.posts[0].title in ['First AsyncPost', 'Second AsyncPost']
        assert loaded_user.posts[1].title in ['First AsyncPost', 'Second AsyncPost']

    @pytest.mark.asyncio
    async def test_get_without_load_relations(self, user_repo, post_repo):
        """Should work without load_relations parameter."""
        user = await user_repo.create({
            'name': 'Jane',
            'email': 'jane@example.com'
        })

        await post_repo.create({
            'title': 'AsyncPost',
            'content': 'Content',
            'user_id': user.id
        })

        # Get without eager loading
        loaded_user = await user_repo.get(user.id)

        assert loaded_user is not None
        assert loaded_user.name == 'Jane'

    @pytest.mark.asyncio
    async def test_get_all_with_load_relations(self, user_repo, post_repo):
        """Should load relationships for all records with get_all()."""
        # Create multiple users with posts
        user1 = await user_repo.create({'name': 'User1', 'email': 'u1@test.com'})
        user2 = await user_repo.create({'name': 'User2', 'email': 'u2@test.com'})
        user3 = await user_repo.create({'name': 'User3', 'email': 'u3@test.com'})

        await post_repo.create({'title': 'Post1', 'content': 'C1', 'user_id': user1.id})
        await post_repo.create({'title': 'Post2', 'content': 'C2', 'user_id': user1.id})
        await post_repo.create({'title': 'Post3', 'content': 'C3', 'user_id': user2.id})

        # Get all users with posts
        users = await user_repo.get_all(load_relations=['posts'])

        assert len(users) == 3

        # Check that posts are loaded
        user_with_2_posts = next(u for u in users if u.id == user1.id)
        assert len(user_with_2_posts.posts) == 2

        user_with_1_post = next(u for u in users if u.id == user2.id)
        assert len(user_with_1_post.posts) == 1

        user_with_0_posts = next(u for u in users if u.id == user3.id)
        assert len(user_with_0_posts.posts) == 0

    @pytest.mark.asyncio
    async def test_filter_with_load_relations(self, user_repo, post_repo):
        """Should load relationships when filtering."""
        # Create users
        active_user = await user_repo.create({
            'name': 'Active',
            'email': 'active@test.com',
            'is_active': True
        })
        inactive_user = await user_repo.create({
            'name': 'Inactive',
            'email': 'inactive@test.com',
            'is_active': False
        })

        await post_repo.create({'title': 'Active AsyncPost', 'content': 'C', 'user_id': active_user.id})
        await post_repo.create({'title': 'Inactive AsyncPost', 'content': 'C', 'user_id': inactive_user.id})

        # Filter active users with posts
        active_users = await user_repo.filter(
            is_active=True,
            _load_relations=['posts']
        )

        assert len(active_users) == 1
        assert active_users[0].name == 'Active'
        assert len(active_users[0].posts) == 1
        assert active_users[0].posts[0].title == 'Active AsyncPost'

    @pytest.mark.asyncio
    async def test_paginate_with_load_relations(self, user_repo, post_repo):
        """Should load relationships when paginating."""
        # Create 5 users with posts
        for i in range(5):
            user = await user_repo.create({
                'name': f'AsyncUser{i}',
                'email': f'user{i}@test.com'
            })
            await post_repo.create({
                'title': f'AsyncPost{i}',
                'content': f'Content{i}',
                'user_id': user.id
            })

        # Paginate with eager loading
        users, meta = await user_repo.paginate(
            page=1,
            per_page=3,
            _load_relations=['posts']
        )

        assert len(users) == 3
        assert meta['total'] == 5
        assert meta['total_pages'] == 2

        # All users should have posts loaded
        for user in users:
            assert len(user.posts) == 1

    @pytest.mark.asyncio
    async def test_get_or_404_with_load_relations(self, user_repo, post_repo):
        """Should load relationships with get_or_404()."""
        user = await user_repo.create({'name': 'Test', 'email': 'test@test.com'})
        await post_repo.create({'title': 'AsyncPost', 'content': 'C', 'user_id': user.id})

        # Get with eager loading
        loaded_user = await user_repo.get_or_404(
            user.id,
            load_relations=['posts']
        )

        assert loaded_user.name == 'Test'
        assert len(loaded_user.posts) == 1
        assert loaded_user.posts[0].title == 'AsyncPost'

    @pytest.mark.asyncio
    async def test_load_relations_none_works(self, user_repo):
        """Should handle load_relations=None gracefully."""
        user = await user_repo.create({'name': 'Test', 'email': 't@test.com'})

        # Should work without error
        loaded = await user_repo.get(user.id, load_relations=None)
        assert loaded is not None
        assert loaded.name == 'Test'

    @pytest.mark.asyncio
    async def test_load_relations_empty_list_works(self, user_repo):
        """Should handle load_relations=[] gracefully."""
        user = await user_repo.create({'name': 'Test', 'email': 't@test.com'})

        loaded = await user_repo.get(user.id, load_relations=[])
        assert loaded is not None
        assert loaded.name == 'Test'

    @pytest.mark.asyncio
    async def test_invalid_relation_name_raises_error(self, user_repo):
        """Should raise AttributeError for invalid relationship name."""
        user = await user_repo.create({'name': 'Test', 'email': 't@test.com'})

        with pytest.raises(AttributeError):
            await user_repo.get(
                user.id,
                load_relations=['nonexistent_relation']
            )

    @pytest.mark.asyncio
    async def test_reverse_relationship_loading(self, user_repo, post_repo):
        """Should load reverse relationships (post.user)."""
        user = await user_repo.create({'name': 'Author', 'email': 'author@test.com'})
        post = await post_repo.create({
            'title': 'My AsyncPost',
            'content': 'Content',
            'user_id': user.id
        })

        # Load post with user
        loaded_post = await post_repo.get(post.id, load_relations=['user'])

        assert loaded_post is not None
        assert loaded_post.user.name == 'Author'
        assert loaded_post.user.email == 'author@test.com'

    @pytest.mark.asyncio
    async def test_filter_with_relations_and_operators(self, user_repo, post_repo):
        """Should combine filters, operators, and eager loading."""
        # Create users with different ages and posts
        young_user = await user_repo.create({'name': 'Young', 'email': 'young@test.com', 'age': 20})
        old_user = await user_repo.create({'name': 'Old', 'email': 'old@test.com', 'age': 50})

        await post_repo.create({'title': 'Young AsyncPost', 'content': 'C', 'user_id': young_user.id})
        await post_repo.create({'title': 'Old AsyncPost', 'content': 'C', 'user_id': old_user.id})

        # Filter users age >= 30 with posts loaded
        users = await user_repo.filter(
            age__gte=30,
            _load_relations=['posts']
        )

        assert len(users) == 1
        assert users[0].name == 'Old'
        assert users[0].age == 50
        assert len(users[0].posts) == 1
        assert users[0].posts[0].title == 'Old AsyncPost'

    @pytest.mark.asyncio
    async def test_paginate_with_filters_and_relations(self, user_repo, post_repo):
        """Should combine pagination, filters, and eager loading."""
        # Create active and inactive users
        for i in range(3):
            user = await user_repo.create({
                'name': f'Active{i}',
                'email': f'active{i}@test.com',
                'is_active': True
            })
            await post_repo.create({'title': f'AsyncPost{i}', 'content': 'C', 'user_id': user.id})

        for i in range(2):
            user = await user_repo.create({
                'name': f'Inactive{i}',
                'email': f'inactive{i}@test.com',
                'is_active': False
            })
            await post_repo.create({'title': f'Inactive AsyncPost{i}', 'content': 'C', 'user_id': user.id})

        # Paginate active users with posts
        users, meta = await user_repo.paginate(
            page=1,
            per_page=2,
            is_active=True,
            _load_relations=['posts']
        )

        assert len(users) == 2
        assert meta['total'] == 3
        assert all(u.is_active for u in users)
        assert all(len(u.posts) == 1 for u in users)

    @pytest.mark.asyncio
    async def test_multiple_get_calls_with_different_relations(self, user_repo, post_repo):
        """Should handle multiple calls with different load_relations."""
        user = await user_repo.create({'name': 'AsyncUser', 'email': 'user@test.com'})
        await post_repo.create({'title': 'AsyncPost', 'content': 'C', 'user_id': user.id})

        # First call without relations
        user1 = await user_repo.get(user.id)
        assert user1 is not None

        # Second call with relations
        user2 = await user_repo.get(user.id, load_relations=['posts'])
        assert user2 is not None
        assert len(user2.posts) == 1

        # Third call without relations again
        user3 = await user_repo.get(user.id)
        assert user3 is not None