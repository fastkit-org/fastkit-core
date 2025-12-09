"""
Comprehensive tests for FastKit Core TranslatableMixin.

Tests multi-language field support:
- Transparent get/set operations
- Locale management (instance and global)
- Translation storage and retrieval
- Fallback behavior
- Database persistence
- Integration with to_dict()
- Validation
- Edge cases

"""

import pytest
import json
from datetime import datetime
from sqlalchemy import create_engine, String, JSON, Integer, ForeignKey
from sqlalchemy.orm import sessionmaker, Mapped, mapped_column, relationship

from fastkit_core.database import Base, IntIdMixin, TranslatableMixin
from fastkit_core.i18n import set_locale, get_locale


# ============================================================================
# Test Models
# ============================================================================

class Article(Base, IntIdMixin, TranslatableMixin):
    """Article with translatable fields."""
    __tablename__ = 'articles'
    __translatable__ = ['title', 'content']

    title: Mapped[dict] = mapped_column(JSON)
    content: Mapped[dict] = mapped_column(JSON)
    author: Mapped[str] = mapped_column(String(100))  # Non-translatable


class Product(Base, IntIdMixin, TranslatableMixin):
    """Product with custom fallback locale."""
    __tablename__ = 'products'
    __translatable__ = ['name', 'description']
    __fallback_locale__ = 'es'  # Custom fallback

    name: Mapped[dict] = mapped_column(JSON)
    description: Mapped[dict] = mapped_column(JSON)
    price: Mapped[int] = mapped_column(Integer)


class Category(Base, IntIdMixin, TranslatableMixin):
    """Category with single translatable field."""
    __tablename__ = 'categories'
    __translatable__ = ['name']

    name: Mapped[dict] = mapped_column(JSON)


class Page(Base, IntIdMixin, TranslatableMixin):
    """Page with relationship."""
    __tablename__ = 'pages'
    __translatable__ = ['title', 'body']

    title: Mapped[dict] = mapped_column(JSON)
    body: Mapped[dict] = mapped_column(JSON)
    category_id: Mapped[int] = mapped_column(ForeignKey('categories.id'))

    category: Mapped[Category] = relationship(Category, backref='pages')


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


@pytest.fixture(autouse=True)
def reset_locale():
    """Reset locale before each test."""
    set_locale('en')
    TranslatableMixin.set_global_locale('en')
    yield
    set_locale('en')
    TranslatableMixin.set_global_locale('en')