"""
Comprehensive tests for FastKit Core Repository pattern.

Tests Repository functionality:
- Basic CRUD operations
- Django-style filtering with operators
- Pagination with metadata
- Bulk operations
- Soft delete support
- Query optimization
- Edge cases and error handling

"""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine, String, Integer, ForeignKey, Boolean
from sqlalchemy.orm import sessionmaker, Mapped, mapped_column, relationship

from fastkit_core.database import (
    Base,
    IntIdMixin,
    Repository,
    SoftDeleteMixin,
    TimestampMixin,
    create_repository,
)


# ============================================================================
# Test Models
# ============================================================================

class User(Base, IntIdMixin, TimestampMixin):
    """User model for testing."""
    __tablename__ = 'users_rep_test'

    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(100), unique=True)
    age: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Post(Base, IntIdMixin, SoftDeleteMixin):
    """Post model with soft delete."""
    __tablename__ = 'posts_rep_test'

    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(String(1000))
    user_id: Mapped[int] = mapped_column(ForeignKey('users_rep_test.id'))
    views: Mapped[int] = mapped_column(Integer, default=0)

    user: Mapped[User] = relationship(User, backref='posts_rep_test')


class Product(Base, IntIdMixin):
    """Product model for filtering tests."""
    __tablename__ = 'products_rep_test'

    name: Mapped[str] = mapped_column(String(100))
    price: Mapped[int] = mapped_column(Integer)
    stock: Mapped[int] = mapped_column(Integer)
    category: Mapped[str] = mapped_column(String(50))

# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def engine():
    """Create in-memory SQLite engine."""
    engine = create_engine('sqlite:///:memory:', echo=False)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    """Create database session."""
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def user_repo(session):
    """Create user repository."""
    return Repository(User, session)


@pytest.fixture
def post_repo(session):
    """Create post repository."""
    return Repository(Post, session)


@pytest.fixture
def product_repo(session):
    """Create product repository."""
    return Repository(Product, session)


@pytest.fixture
def sample_users(user_repo):
    """Create sample users."""
    users = [
        {'name': 'Alice', 'email': 'alice@example.com', 'age': 25, 'is_active': True},
        {'name': 'Bob', 'email': 'bob@example.com', 'age': 30, 'is_active': True},
        {'name': 'Charlie', 'email': 'charlie@example.com', 'age': 35, 'is_active': False},
        {'name': 'David', 'email': 'david@example.com', 'age': 40, 'is_active': True},
        {'name': 'Eve', 'email': 'eve@example.com', 'age': 28, 'is_active': True},
    ]
    return user_repo.create_many(users)


# ============================================================================
# Test Repository Initialization
# ============================================================================

class TestRepositoryInit:
    """Test repository initialization."""

    def test_init_with_model_and_session(self, session):
        """Should initialize with model and session."""
        repo = Repository(User, session)

        assert repo.model == User
        assert repo.session == session

    def test_create_repository_function(self, session):
        """Should create repository with helper function."""
        repo = create_repository(User, session)

        assert isinstance(repo, Repository)
        assert repo.model == User

    def test_repository_repr(self, user_repo):
        """Should have meaningful repr."""
        repr_str = repr(user_repo)

        assert 'Repository' in repr_str


# ============================================================================
# Test CREATE Operations
# ============================================================================

class TestCreateOperations:
    """Test create operations."""

    def test_create_basic(self, user_repo):
        """Should create a record."""
        user = user_repo.create({
            'name': 'John',
            'email': 'john@example.com',
            'age': 30
        })

        assert user.id is not None
        assert user.name == 'John'
        assert user.email == 'john@example.com'

    def test_create_with_commit_true(self, user_repo, session):
        """Should commit when commit=True."""
        user = user_repo.create(
            {'name': 'John', 'email': 'john@example.com', 'age': 30},
            commit=True
        )

        # Should be committed
        session.expire_all()
        found = session.query(User).filter_by(id=user.id).first()
        assert found is not None

    def test_create_with_commit_false(self, user_repo, session):
        """Should not commit when commit=False."""
        user = user_repo.create(
            {'name': 'John', 'email': 'john@example.com', 'age': 30},
            commit=False
        )

        # Rollback
        session.rollback()

        # Should not exist
        found = session.query(User).filter_by(id=user.id).first()
        assert found is None

    def test_create_many(self, user_repo):
        """Should create multiple records."""
        users_data = [
            {'name': f'User{i}', 'email': f'user{i}@example.com', 'age': 20 + i}
            for i in range(5)
        ]

        users = user_repo.create_many(users_data)

        assert len(users) == 5
        assert all(u.id is not None for u in users)

    def test_create_many_with_commit_false(self, user_repo, session):
        """Should not commit bulk create when commit=False."""
        users_data = [
            {'name': f'User{i}', 'email': f'user{i}@example.com', 'age': 20 + i}
            for i in range(3)
        ]

        users = user_repo.create_many(users_data, commit=False)

        # Rollback
        session.rollback()

        # Should not exist
        count = session.query(User).count()
        assert count == 0

    def test_create_with_defaults(self, user_repo):
        """Should use model defaults."""
        user = user_repo.create({
            'name': 'John',
            'email': 'john@example.com',
            'age': 30
        })

        # is_active has default=True
        assert user.is_active is True

    def test_create_with_timestamps(self, user_repo):
        """Should auto-set timestamps."""
        user = user_repo.create({
            'name': 'John',
            'email': 'john@example.com',
            'age': 30
        })

        assert user.created_at is not None
        assert user.updated_at is not None


# ============================================================================
# Test READ Operations
# ============================================================================

class TestReadOperations:
    """Test read operations."""

    def test_get_by_id(self, user_repo, sample_users):
        """Should get record by ID."""
        user = user_repo.get(sample_users[0].id)

        assert user is not None
        assert user.id == sample_users[0].id
        assert user.name == sample_users[0].name

    def test_get_nonexistent(self, user_repo):
        """Should return None for nonexistent ID."""
        user = user_repo.get(9999)

        assert user is None

    def test_get_all(self, user_repo, sample_users):
        """Should get all records."""
        users = user_repo.get_all()

        assert len(users) == len(sample_users)

    def test_get_all_with_limit(self, user_repo, sample_users):
        """Should limit results."""
        users = user_repo.get_all(limit=3)

        assert len(users) == 3

    def test_first(self, user_repo, sample_users):
        """Should get first record."""
        user = user_repo.filter_one()

        assert user is not None
        assert user.id == sample_users[0].id

    def test_first_empty_table(self, user_repo):
        """Should return None for empty table."""
        user = user_repo.filter_one()

        assert user is None


# ============================================================================
# Test FILTER Operations
# ============================================================================

class TestFilterOperations:
    """Test filtering with Django-style operators."""

    def test_filter_exact_match(self, user_repo, sample_users):
        """Should filter by exact value."""
        users = user_repo.filter(name='Alice')

        assert len(users) == 1
        assert users[0].name == 'Alice'

    def test_filter_multiple_conditions(self, user_repo, sample_users):
        """Should filter by multiple conditions (AND)."""
        users = user_repo.filter(is_active=True, age=25)

        assert len(users) == 1
        assert users[0].name == 'Alice'

    def test_filter_gt_operator(self, user_repo, sample_users):
        """Should filter with greater than."""
        users = user_repo.filter(age__gt=30)

        assert len(users) == 2  # Charlie (35) and David (40)
        assert all(u.age > 30 for u in users)

    def test_filter_gte_operator(self, user_repo, sample_users):
        """Should filter with greater than or equal."""
        users = user_repo.filter(age__gte=30)

        assert len(users) == 3  # Bob (30), Charlie (35), David (40)
        assert all(u.age >= 30 for u in users)

    def test_filter_lt_operator(self, user_repo, sample_users):
        """Should filter with less than."""
        users = user_repo.filter(age__lt=30)

        assert len(users) == 2  # Alice (25), Eve (28)
        assert all(u.age < 30 for u in users)

    def test_filter_lte_operator(self, user_repo, sample_users):
        """Should filter with less than or equal."""
        users = user_repo.filter(age__lte=30)

        assert len(users) == 3  # Alice (25), Eve (28), Bob (30)
        assert all(u.age <= 30 for u in users)

    def test_filter_in_operator(self, user_repo, sample_users):
        """Should filter with IN clause."""
        users = user_repo.filter(name__in=['Alice', 'Bob', 'Charlie'])

        assert len(users) == 3
        names = [u.name for u in users]
        assert 'Alice' in names
        assert 'Bob' in names
        assert 'Charlie' in names

    def test_filter_not_in_operator(self, user_repo, sample_users):
        """Should filter with NOT IN clause."""
        users = user_repo.filter(name__not_in=['Alice', 'Bob'])

        assert len(users) == 3
        names = [u.name for u in users]
        assert 'Alice' not in names
        assert 'Bob' not in names

    def test_filter_like_operator(self, user_repo, sample_users):
        """Should filter with LIKE (case-insensitive contains)."""
        users = user_repo.filter(name__like='%li%')

        assert len(users) == 2  # Alice, Charlie
        assert all('li' in u.name.lower() for u in users)

    def test_filter_ilike_operator(self, user_repo, sample_users):
        """Should filter with ILIKE (case-insensitive)."""
        users = user_repo.filter(name__ilike='%ALICE%')

        assert len(users) == 1
        assert users[0].name == 'Alice'

    def test_filter_startswith(self, user_repo, sample_users):
        """Should filter with startswith."""
        users = user_repo.filter(name__startswith='A')

        assert len(users) == 1
        assert users[0].name == 'Alice'

    def test_filter_endswith(self, user_repo, sample_users):
        """Should filter with endswith."""
        users = user_repo.filter(email__endswith='example.com')

        assert len(users) == 5  # All emails

    def test_filter_is_null(self, user_repo):
        """Should filter for NULL values."""

        # Create user with optional field
        class UserWithOptional(Base, IntIdMixin):
            __tablename__ = 'users_optional'
            name: Mapped[str] = mapped_column(String(100))
            nickname: Mapped[str | None] = mapped_column(String(100), nullable=True)

        Base.metadata.create_all(user_repo.session.bind)

        repo = Repository(UserWithOptional, user_repo.session)
        repo.create({'name': 'John', 'nickname': None})
        repo.create({'name': 'Jane', 'nickname': 'JJ'})

        users = repo.filter(nickname__is_null=True)

        assert len(users) == 1
        assert users[0].name == 'John'

    def test_filter_is_not_null(self, user_repo, sample_users):
        """Should filter for NOT NULL values."""
        users = user_repo.filter(name__is_not_null=True)

        # All users have names
        assert len(users) > 0

    def test_filter_with_limit(self, user_repo, sample_users):
        """Should limit filter results."""
        users = user_repo.filter(is_active=True, _limit=2)

        assert len(users) == 2

    def test_filter_with_offset(self, user_repo, sample_users):
        """Should offset filter results."""
        users = user_repo.filter(is_active=True, _offset=2, _limit=2)

        assert len(users) == 2

    def test_filter_with_order_by_asc(self, user_repo, sample_users):
        """Should order by ascending."""
        users = user_repo.filter(_order_by='age')

        assert users[0].age == 25  # Alice
        assert users[-1].age == 40  # David
        # Verify ascending order
        ages = [u.age for u in users]
        assert ages == sorted(ages)

    def test_filter_with_order_by_desc(self, user_repo, sample_users):
        """Should order by descending."""
        users = user_repo.filter(_order_by='-age')

        assert users[0].age == 40  # David
        assert users[-1].age == 25  # Alice
        # Verify descending order
        ages = [u.age for u in users]
        assert ages == sorted(ages, reverse=True)

    def test_filter_one(self, user_repo, sample_users):
        """Should get first matching record."""
        user = user_repo.filter_one(name='Alice')

        assert user is not None
        assert user.name == 'Alice'

    def test_filter_one_not_found(self, user_repo, sample_users):
        """Should return None when not found."""
        user = user_repo.filter_one(name='Nonexistent')

        assert user is None

    def test_filter_no_matches(self, user_repo, sample_users):
        """Should return empty list when no matches."""
        users = user_repo.filter(age=999)

        assert users == []


# ============================================================================
# Test PAGINATION
# ============================================================================

class TestPagination:
    """Test pagination functionality."""

    def test_paginate_first_page(self, user_repo):
        """Should paginate first page."""
        # Create 25 users
        users_data = [
            {'name': f'User{i}', 'email': f'user{i}@example.com', 'age': 20}
            for i in range(25)
        ]
        user_repo.create_many(users_data)

        users, meta = user_repo.paginate(page=1, per_page=10)

        assert len(users) == 10
        assert meta['page'] == 1
        assert meta['per_page'] == 10
        assert meta['total'] == 25
        assert meta['total_pages'] == 3
        assert meta['has_next'] is True
        assert meta['has_prev'] is False

    def test_paginate_middle_page(self, user_repo):
        """Should paginate middle page."""
        users_data = [
            {'name': f'User{i}', 'email': f'user{i}@example.com', 'age': 20}
            for i in range(25)
        ]
        user_repo.create_many(users_data)

        users, meta = user_repo.paginate(page=2, per_page=10)

        assert len(users) == 10
        assert meta['page'] == 2
        assert meta['has_next'] is True
        assert meta['has_prev'] is True

    def test_paginate_last_page(self, user_repo):
        """Should paginate last page."""
        users_data = [
            {'name': f'User{i}', 'email': f'user{i}@example.com', 'age': 20}
            for i in range(25)
        ]
        user_repo.create_many(users_data)

        users, meta = user_repo.paginate(page=3, per_page=10)

        assert len(users) == 5  # Remaining items
        assert meta['page'] == 3
        assert meta['has_next'] is False
        assert meta['has_prev'] is True

    def test_paginate_with_filters(self, user_repo, sample_users):
        """Should paginate filtered results."""
        users, meta = user_repo.paginate(
            page=1,
            per_page=2,
            is_active=True
        )

        assert len(users) <= 2
        assert all(u.is_active for u in users)
        assert meta['total'] == 4  # 4 active users

    def test_paginate_empty_results(self, user_repo):
        """Should handle empty results."""
        users, meta = user_repo.paginate(page=1, per_page=10)

        assert users == []
        assert meta['total'] == 0
        assert meta['total_pages'] == 0
        assert meta['has_next'] is False
        assert meta['has_prev'] is False

    def test_paginate_beyond_last_page(self, user_repo, sample_users):
        """Should handle page beyond total pages."""
        users, meta = user_repo.paginate(page=100, per_page=10)

        assert users == []
        assert meta['page'] == 100


# ============================================================================
# Test UPDATE Operations
# ============================================================================

class TestUpdateOperations:
    """Test update operations."""

    def test_update_by_id(self, user_repo, sample_users):
        """Should update record by ID."""
        user = sample_users[0]

        updated = user_repo.update(user.id, {'name': 'Updated Name'})

        assert updated is not None
        assert updated.name == 'Updated Name'
        assert updated.email == user.email  # Unchanged

    def test_update_multiple_fields(self, user_repo, sample_users):
        """Should update multiple fields."""
        user = sample_users[0]

        updated = user_repo.update(user.id, {
            'name': 'New Name',
            'age': 99
        })

        assert updated.name == 'New Name'
        assert updated.age == 99

    def test_update_nonexistent(self, user_repo):
        """Should return None for nonexistent ID."""
        updated = user_repo.update(9999, {'name': 'Nobody'})

        assert updated is None

    def test_update_with_commit_false(self, user_repo, sample_users, session):
        """Should not commit when commit=False."""
        user = sample_users[0]
        original_name = user.name

        user_repo.update(user.id, {'name': 'Changed'}, commit=False)

        # Rollback
        session.rollback()

        # Should be unchanged
        session.expire_all()
        found = user_repo.get(user.id)
        assert found.name == original_name

    def test_update_many(self, user_repo, sample_users):
        """Should update multiple records."""
        count = user_repo.update_many(
            filters={'is_active': True},
            data={'age': 50}
        )

        assert count == 4  # 4 active users

        # Verify
        active_users = user_repo.filter(is_active=True)
        assert all(u.age == 50 for u in active_users)

    def test_update_many_no_matches(self, user_repo, sample_users):
        """Should return 0 when no matches."""
        count = user_repo.update_many(
            filters={'name': 'Nonexistent'},
            data={'age': 99}
        )

        assert count == 0


# ============================================================================
# Test DELETE Operations
# ============================================================================

class TestDeleteOperations:
    """Test delete operations."""

    def test_delete_by_id(self, user_repo, sample_users):
        """Should delete record by ID."""
        user = sample_users[0]

        deleted = user_repo.delete(user.id)

        assert deleted is True

        # Verify deleted
        found = user_repo.get(user.id)
        assert found is None

    def test_delete_nonexistent(self, user_repo):
        """Should return False for nonexistent ID."""
        deleted = user_repo.delete(9999)

        assert deleted is False

    def test_delete_with_commit_false(self, user_repo, sample_users, session):
        """Should not commit when commit=False."""
        user = sample_users[0]

        user_repo.delete(user.id, commit=False)

        # Rollback
        session.rollback()

        # Should still exist
        found = user_repo.get(user.id)
        assert found is not None

    def test_delete_many(self, user_repo, sample_users):
        """Should delete multiple records."""
        count = user_repo.delete_many(filters={'is_active': False})

        assert count == 1  # Charlie is inactive

        # Verify
        remaining = user_repo.get_all()
        assert len(remaining) == 4

    def test_delete_many_no_matches(self, user_repo, sample_users):
        """Should return 0 when no matches."""
        count = user_repo.delete_many(filters={'name': 'Nonexistent'})

        assert count == 0


# ============================================================================
# Test Soft Delete Support
# ============================================================================

class TestSoftDelete:
    """Test soft delete functionality."""

    def test_soft_delete_basic(self, post_repo, sample_users):
        """Should soft delete by default."""
        post = post_repo.create({
            'title': 'Test Post',
            'content': 'Content',
            'user_id': sample_users[0].id
        })

        # Delete (soft)
        deleted = post_repo.delete(post.id)

        assert deleted is True

        # Should not be in regular queries
        found = post_repo.get(post.id)
        assert found is None

        # But should exist in database with deleted_at set
        all_posts = post_repo.session.query(Post).filter_by(id=post.id).first()
        assert all_posts is not None
        assert all_posts.deleted_at is not None

    def test_force_delete(self, post_repo, sample_users):
        """Should force delete when force=True."""
        post = post_repo.create({
            'title': 'Test Post',
            'content': 'Content',
            'user_id': sample_users[0].id
        })

        # Force delete
        deleted = post_repo.delete(post.id, force=True)

        assert deleted is True

        # Should be completely gone from database
        all_posts = post_repo.session.query(Post).filter_by(id=post.id).first()
        assert all_posts is None

    def test_filter_excludes_soft_deleted(self, post_repo, sample_users):
        """Should exclude soft deleted records from filter."""
        post1 = post_repo.create({
            'title': 'Active Post',
            'content': 'Content',
            'user_id': sample_users[0].id
        })

        post2 = post_repo.create({
            'title': 'Deleted Post',
            'content': 'Content',
            'user_id': sample_users[0].id
        })

        # Soft delete post2
        post_repo.delete(post2.id)

        # Filter should only return active
        posts = post_repo.filter()

        assert len(posts) == 1
        assert posts[0].id == post1.id

    def test_get_all_excludes_soft_deleted(self, post_repo, sample_users):
        """Should exclude soft deleted from get_all."""
        post1 = post_repo.create({
            'title': 'Active',
            'content': 'Content',
            'user_id': sample_users[0].id
        })

        post2 = post_repo.create({
            'title': 'Deleted',
            'content': 'Content',
            'user_id': sample_users[0].id
        })

        post_repo.delete(post2.id)

        posts = post_repo.get_all()

        assert len(posts) == 1


# ============================================================================
# Test EXISTS and COUNT
# ============================================================================

class TestExistsAndCount:
    """Test exists and count operations."""

    def test_exists_true(self, user_repo, sample_users):
        """Should return True when record exists."""
        exists = user_repo.exists(name='Alice')

        assert exists is True

    def test_exists_false(self, user_repo, sample_users):
        """Should return False when not exists."""
        exists = user_repo.exists(name='Nonexistent')

        assert exists is False

    def test_exists_with_multiple_conditions(self, user_repo, sample_users):
        """Should check multiple conditions."""
        exists = user_repo.exists(name='Alice', age=25)

        assert exists is True

    def test_count_all(self, user_repo, sample_users):
        """Should count all records."""
        count = user_repo.count()

        assert count == 5

    def test_count_with_filters(self, user_repo, sample_users):
        """Should count filtered records."""
        count = user_repo.count(is_active=True)

        assert count == 4

    def test_count_with_operators(self, user_repo, sample_users):
        """Should count with filter operators."""
        count = user_repo.count(age__gte=30)

        assert count == 3


# ============================================================================
# Test Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_create_empty_dict(self, user_repo):
        """Should handle empty dict gracefully."""
        with pytest.raises(Exception):
            # Will fail due to missing required fields
            user_repo.create({})

    def test_update_with_empty_dict(self, user_repo, sample_users):
        """Should handle empty update dict."""
        user = sample_users[0]
        original_name = user.name

        updated = user_repo.update(user.id, {})

        # Should still return the instance
        assert updated is not None
        assert updated.name == original_name

    def test_paginate_page_zero(self, user_repo, sample_users):
        """Should handle page 0."""
        users, meta = user_repo.paginate(page=0, per_page=10)

        # Should treat as page 1 or handle gracefully
        assert isinstance(users, list)

    def test_paginate_negative_page(self, user_repo, sample_users):
        """Should handle negative page."""
        users, meta = user_repo.paginate(page=-1, per_page=10)

        # Should handle gracefully
        assert isinstance(users, list)

    def test_very_large_limit(self, user_repo, sample_users):
        """Should handle very large limit."""
        users = user_repo.filter(_limit=999999)

        assert len(users) == 5  # Only 5 users exist


# ============================================================================
# Test Integration Scenarios
# ============================================================================

class TestIntegration:
    """Test real-world integration scenarios."""

    def test_crud_lifecycle(self, user_repo):
        """Should handle complete CRUD lifecycle."""
        # Create
        user = user_repo.create({
            'name': 'John',
            'email': 'john@example.com',
            'age': 30
        })
        assert user.id is not None

        # Read
        found = user_repo.get(user.id)
        assert found.name == 'John'

        # Update
        updated = user_repo.update(user.id, {'age': 31})
        assert updated.age == 31

        # Delete
        deleted = user_repo.delete(user.id)
        assert deleted is True

        # Verify deleted
        assert user_repo.get(user.id) is None

    def test_complex_filtering(self, product_repo):
        """Should handle complex filtering scenarios."""
        # Create products
        products = [
            {'name': 'Laptop', 'price': 1000, 'stock': 10, 'category': 'Electronics'},
            {'name': 'Phone', 'price': 500, 'stock': 20, 'category': 'Electronics'},
            {'name': 'Desk', 'price': 300, 'stock': 5, 'category': 'Furniture'},
            {'name': 'Chair', 'price': 150, 'stock': 15, 'category': 'Furniture'},
        ]
        product_repo.create_many(products)

        # Complex filter: Electronics, price < 600, in stock
        results = product_repo.filter(
            category='Electronics',
            price__lt=600,
            stock__gte=10
        )

        assert len(results) == 1
        assert results[0].name == 'Phone'

    def test_pagination_with_sorting(self, user_repo):
        """Should combine pagination with sorting."""
        users_data = [
            {'name': f'User{i}', 'email': f'user{i}@example.com', 'age': 20 + (i % 10)}
            for i in range(30)
        ]
        user_repo.create_many(users_data)

        # Page 2, sorted by age descending
        users, meta = user_repo.paginate(
            page=2,
            per_page=10,
            _order_by='-age'
        )

        assert len(users) == 10
        # Should be sorted descending
        ages = [u.age for u in users]
        assert ages == sorted(ages, reverse=True)

    def test_bulk_operations(self, user_repo):
        """Should handle bulk operations efficiently."""
        # Bulk create
        users_data = [
            {'name': f'User{i}', 'email': f'user{i}@example.com', 'age': 20}
            for i in range(100)
        ]
        users = user_repo.create_many(users_data)
        assert len(users) == 100

        # Bulk update
        count = user_repo.update_many(
            filters={'age': 20},
            data={'age': 21}
        )
        assert count == 100

        # Verify
        assert user_repo.count(age=21) == 100