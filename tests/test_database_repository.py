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