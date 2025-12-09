"""
Comprehensive tests for FastKit Core Database Base model.

Tests Base model functionality:
- Auto-generated table names
- Primary key
- Dict serialization
- Relationship handling
- Update from dict
"""

import pytest
from datetime import datetime
from sqlalchemy import create_engine, String, Integer, ForeignKey
from sqlalchemy.orm import sessionmaker, Mapped, mapped_column, relationship

from fastkit_core.database import Base


# ============================================================================
# Test Models
# ============================================================================

class User(Base):
    """Test user model."""
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(100))


class UserProfile(Base):
    """Test model with CamelCase name."""
    bio: Mapped[str] = mapped_column(String(500))


class Category(Base):
    """Test model ending in 'y'."""
    name: Mapped[str] = mapped_column(String(100))


class Post(Base):
    """Test model with relationships."""
    title: Mapped[str] = mapped_column(String(200))
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))

    # Relationship
    user: Mapped[User] = relationship(User, backref='posts')


class Comment(Base):
    """Test model with nested relationships."""
    content: Mapped[str] = mapped_column(String(500))
    post_id: Mapped[int] = mapped_column(ForeignKey('posts.id'))

    post: Mapped[Post] = relationship(Post, backref='comments')

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
    session.close()

# ============================================================================
# Test Table Name Generation
# ============================================================================

class TestTableNames:
    """Test automatic table name generation."""

    def test_simple_name(self):
        """Should pluralize simple names."""
        assert User.__tablename__ == 'users'

    def test_camelcase_name(self):
        """Should convert CamelCase to snake_case and pluralize."""
        assert UserProfile.__tablename__ == 'user_profiles'

    def test_name_ending_in_y(self):
        """Should handle names ending in 'y'."""
        assert Category.__tablename__ == 'categories'

    def test_name_ending_in_s(self):
        """Should handle names ending in 's'."""

        class Status(Base):
            name: Mapped[str] = mapped_column(String(50))

        assert Status.__tablename__ == 'statuses'

    def test_custom_tablename(self):
        """Should allow custom table name override."""

        class CustomModel(Base):
            __tablename_override__ = 'my_custom_table'
            name: Mapped[str] = mapped_column(String(50))

        assert CustomModel.__tablename__ == 'my_custom_table'


# ============================================================================
# Test Primary Key
# ============================================================================

class TestPrimaryKey:
    """Test primary key functionality."""

    def test_has_id_column(self, session):
        """Should have auto-incrementing id."""
        user = User(name="John", email="john@example.com")
        session.add(user)
        session.commit()

        assert user.id is not None
        assert isinstance(user.id, int)
        assert user.id > 0

    def test_auto_increment(self, session):
        """Should auto-increment IDs."""
        user1 = User(name="John", email="john@example.com")
        user2 = User(name="Jane", email="jane@example.com")

        session.add(user1)
        session.add(user2)
        session.commit()

        assert user2.id == user1.id + 1

