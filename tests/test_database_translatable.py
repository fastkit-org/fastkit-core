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


# ============================================================================
# Test Basic Get/Set Operations
# ============================================================================

class TestBasicGetSet:
    """Test basic get/set operations."""

    def test_set_single_locale(self, session):
        """Should set translation for current locale."""
        article = Article(author="John")
        session.add(article)  # Add to session FIRST
        session.flush()  # Ensure it's tracked

        article.title = "Hello World"

        assert article.title == "Hello World"

    def test_set_multiple_locales(self, session):
        """Should set translations for multiple locales."""
        article = Article(author="John")
        session.add(article)  # Add to session FIRST
        session.flush()

        set_locale('en')
        article.title = "Hello World"

        set_locale('es')
        article.title = "Hola Mundo"

        set_locale('fr')
        article.title = "Bonjour le Monde"

        # Verify all are stored
        set_locale('en')
        assert article.title == "Hello World"

        set_locale('es')
        assert article.title == "Hola Mundo"

        set_locale('fr')
        assert article.title == "Bonjour le Monde"

    def test_set_multiple_fields(self, session):
        """Should handle multiple translatable fields."""
        article = Article(author="John")

        set_locale('en')
        article.title = "Hello"
        article.content = "Content in English"

        assert article.title == "Hello"
        assert article.content == "Content in English"

    def test_get_fallback_translation(self, session):
        """Should return None for non-existent translation."""
        article = Article(author="John")

        set_locale('en')
        article.title = "Hello"

        set_locale('fr')
        # No French translation set
        assert article.title == "Hello"

    def test_non_translatable_field_works_normally(self, session):
        """Should handle non-translatable fields normally."""
        article = Article(author="John")
        article.title = "Test"

        # Author is not translatable
        assert article.author == "John"

        # Should work the same regardless of locale
        set_locale('es')
        assert article.author == "John"


# ============================================================================
# Test Locale Management
# ============================================================================

class TestLocaleManagement:
    """Test locale management."""

    def test_get_locale_default(self, session):
        """Should return default locale."""
        article = Article(author="John")

        locale = article.get_locale()

        assert locale == 'en'

    def test_set_locale_instance(self, session):
        """Should set instance-specific locale."""
        article = Article(author="John")

        article.set_locale('es')

        assert article.get_locale() == 'es'

    def test_set_locale_chainable(self, session):
        """Should return self for chaining."""
        article = Article(author="John")

        result = article.set_locale('es')

        assert result is article

    def test_instance_locale_overrides_global(self, session):
        """Should prioritize instance locale over global."""
        article = Article(author="John")

        # Set global locale
        TranslatableMixin.set_global_locale('en')

        # Set instance locale
        article.set_locale('es')

        assert article.get_locale() == 'es'

    def test_global_locale_affects_all_instances(self, session):
        """Should affect all instances without instance locale."""
        article1 = Article(author="John")
        article2 = Article(author="Jane")

        TranslatableMixin.set_global_locale('es')

        assert article1.get_locale() == 'es'
        assert article2.get_locale() == 'es'

    def test_get_global_locale(self, session):
        """Should get current global locale."""
        TranslatableMixin.set_global_locale('fr')

        assert TranslatableMixin.get_global_locale() == 'fr'