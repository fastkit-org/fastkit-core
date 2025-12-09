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

