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
    __tablename__ = 'users'

    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(100), unique=True)
    age: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Post(Base, IntIdMixin, SoftDeleteMixin):
    """Post model with soft delete."""
    __tablename__ = 'posts'

    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(String(1000))
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    views: Mapped[int] = mapped_column(Integer, default=0)

    user: Mapped[User] = relationship(User, backref='posts')


class Product(Base, IntIdMixin):
    """Product model for filtering tests."""
    __tablename__ = 'products'

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