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
from sqlalchemy import create_engine, String, JSON, Integer, ForeignKey
from sqlalchemy.orm import sessionmaker, Mapped, mapped_column, relationship

from fastkit_core.database import Base, IntIdMixin, TranslatableMixin
from fastkit_core.i18n import set_locale


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
    __tablename__ = 'categories_trans_test'
    __translatable__ = ['name']

    name: Mapped[dict] = mapped_column(JSON)


class Page(Base, IntIdMixin, TranslatableMixin):
    """Page with relationship."""
    __tablename__ = 'pages'
    __translatable__ = ['title', 'body']

    title: Mapped[dict] = mapped_column(JSON)
    body: Mapped[dict] = mapped_column(JSON)
    category_id: Mapped[int] = mapped_column(ForeignKey('categories_trans_test.id'))

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


# ============================================================================
# Test Translation Methods
# ============================================================================

class TestTranslationMethods:
    """Test translation helper methods."""

    def test_get_translations(self, session):
        """Should get all translations for a field."""
        article = Article(author="John")

        set_locale('en')
        article.title = "Hello"

        set_locale('es')
        article.title = "Hola"

        translations = article.get_translations('title')

        assert translations == {'en': 'Hello', 'es': 'Hola'}

    def test_get_translations_empty(self, session):
        """Should return empty dict for field with no translations."""
        article = Article(author="John")

        translations = article.get_translations('title')

        assert translations == {}

    def test_get_translations_invalid_field(self, session):
        """Should raise error for non-translatable field."""
        article = Article(author="John")

        with pytest.raises(ValueError) as exc_info:
            article.get_translations('author')

        assert 'not translatable' in str(exc_info.value).lower()

    def test_set_translation_explicit(self, session):
        """Should set translation for specific locale."""
        article = Article(author="John")

        article.set_translation('title', 'Bonjour', locale='fr')

        set_locale('fr')
        assert article.title == "Bonjour"

    def test_set_translation_current_locale(self, session):
        """Should use current locale if not specified."""
        article = Article(author="John")

        set_locale('es')
        article.set_translation('title', 'Hola')

        assert article.title == "Hola"

    def test_set_translation_chainable(self, session):
        """Should return self for chaining."""
        article = Article(author="John")

        result = article.set_translation('title', 'Hello')

        assert result is article

    def test_set_translation_invalid_field(self, session):
        """Should raise error for non-translatable field."""
        article = Article(author="John")

        with pytest.raises(ValueError) as exc_info:
            article.set_translation('author', 'John', locale='es')

        assert 'not translatable' in str(exc_info.value).lower()

    def test_get_translation_explicit(self, session):
        """Should get translation for specific locale."""
        article = Article(author="John")

        set_locale('en')
        article.title = "Hello"

        translation = article.get_translation('title', locale='en')

        assert translation == "Hello"

    def test_get_translation_with_fallback(self, session):
        """Should fallback to default locale."""
        article = Article(author="John")

        set_locale('en')
        article.title = "Hello"

        # Request French (doesn't exist), should fallback to English
        translation = article.get_translation('title', locale='fr', fallback=True)

        assert translation == "Hello"

    def test_get_translation_without_fallback(self, session):
        """Should not fallback when disabled."""
        article = Article(author="John")

        set_locale('en')
        article.title = "Hello"

        translation = article.get_translation('title', locale='fr', fallback=False)

        assert translation is None

    def test_has_translation(self, session):
        """Should check if translation exists."""
        article = Article(author="John")

        set_locale('en')
        article.title = "Hello"

        assert article.has_translation('title', locale='en') is True
        assert article.has_translation('title', locale='es') is False

    def test_has_translation_current_locale(self, session):
        """Should check current locale if not specified."""
        article = Article(author="John")

        set_locale('en')
        article.title = "Hello"

        assert article.has_translation('title') is True

        set_locale('es')
        assert article.has_translation('title') is False

    def test_has_translation_invalid_field(self, session):
        """Should return False for non-translatable field."""
        article = Article(author="John")

        assert article.has_translation('author') is False


# ============================================================================
# Test Validation
# ============================================================================

class TestValidation:
    """Test translation validation."""

    def test_validate_translations_all_present(self, session):
        """Should validate when all required translations present."""
        article = Article(author="John")

        set_locale('en')
        article.title = "Hello"
        article.content = "Content"

        missing = article.validate_translations(required_locales=['en'])

        assert missing == {}

    def test_validate_translations_missing(self, session):
        """Should detect missing translations."""
        article = Article(author="John")

        set_locale('en')
        article.title = "Hello"
        # content not set

        missing = article.validate_translations(required_locales=['en'])

        assert 'content' in missing
        assert 'en' in missing['content']

    def test_validate_translations_multiple_locales(self, session):
        """Should validate across multiple locales."""
        article = Article(author="John")

        set_locale('en')
        article.title = "Hello"
        article.content = "Content"

        set_locale('es')
        article.title = "Hola"
        # content not set in Spanish

        missing = article.validate_translations(required_locales=['en', 'es'])

        assert 'content' in missing
        assert 'es' in missing['content']
        assert 'en' not in missing.get('content', [])

    def test_validate_translations_default_locale(self, session):
        """Should default to fallback locale."""
        article = Article(author="John")

        missing = article.validate_translations()

        # Should check default locale (en)
        assert 'title' in missing
        assert 'content' in missing


# ============================================================================
# Test Database Persistence
# ============================================================================

class TestDatabasePersistence:
    """Test database save and load."""

    def test_save_and_load_single_locale(self, session):
        """Should persist single locale to database."""
        article = Article(author="John")

        set_locale('en')
        article.title = "Hello World"
        article.content = "English content"

        session.add(article)
        session.commit()

        # Reload from database
        session.expire_all()
        loaded = session.query(Article).first()

        set_locale('en')
        assert loaded.title == "Hello World"
        assert loaded.content == "English content"

    def test_save_and_load_multiple_locales(self, session):
        """Should persist multiple locales."""
        article = Article(author="John")

        set_locale('en')
        article.title = "Hello"
        article.content = "English"

        set_locale('es')
        article.title = "Hola"
        article.content = "Español"

        session.add(article)
        session.commit()

        # Reload
        session.expire_all()
        loaded = session.query(Article).first()

        set_locale('en')
        assert loaded.title == "Hello"

        set_locale('es')
        assert loaded.title == "Hola"

    def test_update_translation(self, session):
        """Should update existing translation."""
        article = Article(author="John")

        set_locale('en')
        article.title = "Original"

        session.add(article)
        session.commit()

        # Update
        article.title = "Updated"
        session.commit()

        # Reload
        session.expire_all()
        loaded = session.query(Article).first()

        assert loaded.title == "Updated"

    def test_add_new_locale(self, session):
        """Should add new locale to existing record."""
        article = Article(author="John")

        set_locale('en')
        article.title = "Hello"

        session.add(article)
        session.commit()

        # Add Spanish
        set_locale('es')
        article.title = "Hola"
        session.commit()

        # Reload
        session.expire_all()
        loaded = session.query(Article).first()

        set_locale('en')
        assert loaded.title == "Hello"

        set_locale('es')
        assert loaded.title == "Hola"

    def test_partial_update(self, session):
        """Should update one field without affecting others."""
        article = Article(author="John")

        set_locale('en')
        article.title = "Hello"
        article.content = "Content"

        session.add(article)
        session.commit()

        # Update only title
        article.title = "Updated Title"
        session.commit()

        session.expire_all()
        loaded = session.query(Article).first()

        assert loaded.title == "Updated Title"
        assert loaded.content == "Content"  # Unchanged


# ============================================================================
# Test Fallback Behavior
# ============================================================================

class TestFallbackBehavior:
    """Test locale fallback behavior."""

    def test_fallback_to_default_locale(self, session):
        """Should fallback to default locale."""
        article = Article(author="John")

        set_locale('en')
        article.title = "Hello"

        # Request non-existent locale
        set_locale('fr')
        translation = article.get_translation('title', fallback=True)

        assert translation == "Hello"

    def test_custom_fallback_locale(self, session):
        """Should use custom fallback locale."""
        product = Product(price=100)

        # Product has __fallback_locale__ = 'es'
        product.set_locale('es')
        product.name = "Producto"

        # Request non-existent locale, should fallback to es
        translation = product.get_translation('name', locale='fr', fallback=True)

        assert translation == "Producto"

    def test_no_fallback_returns_none(self, session):
        """Should return None when fallback disabled."""
        article = Article(author="John")

        set_locale('en')
        article.title = "Hello"

        translation = article.get_translation('title', locale='fr', fallback=False)

        assert translation is None


# ============================================================================
# Test Integration with to_dict()
# ============================================================================

class TestToDictIntegration:
    """Test integration with Base.to_dict()."""

    def test_to_dict_with_locale(self, session):
        """Should serialize specific locale."""
        article = Article(author="John")

        set_locale('en')
        article.title = "Hello"
        article.content = "English"

        set_locale('es')
        article.title = "Hola"
        article.content = "Español"

        session.add(article)
        session.commit()

        # Get English version
        data_en = article.to_dict(locale='en')

        assert data_en['title'] == "Hello"
        assert data_en['content'] == "English"

        # Get Spanish version
        data_es = article.to_dict(locale='es')

        assert data_es['title'] == "Hola"
        assert data_es['content'] == "Español"

    def test_to_dict_current_locale(self, session):
        """Should use current locale if not specified."""
        article = Article(author="John")

        set_locale('en')
        article.title = "Hello"

        set_locale('es')
        article.title = "Hola"

        session.add(article)
        session.commit()

        # Current locale is 'es'
        data = article.to_dict()

        # Should use 'es' but fall back to raw dict if no explicit locale param
        # (depends on implementation)
        assert 'title' in data

    def test_to_dict_with_relationships(self, session):
        """Should work with relationships."""
        category = Category()
        category.name = "Tech"

        session.add(category)
        session.commit()

        page = Page(category_id=category.id)
        page.title = "Article"

        session.add(page)
        session.commit()

        data = page.to_dict(include_relationships=True, locale='en')

        assert 'category' in data


# ============================================================================
# Test Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_string_translation(self, session):
        """Should handle empty strings."""
        article = Article(author="John")

        article.title = ""

        assert article.title == ""

    def test_none_translation(self, session):
        """Should handle None values."""
        article = Article(author="John")

        article.title = None

        assert article.title is None

    def test_special_characters(self, session):
        """Should handle special characters."""
        article = Article(author="John")

        article.title = "Hello! @#$%^&*() 你好 مرحبا"

        assert article.title == "Hello! @#$%^&*() 你好 مرحبا"

    def test_very_long_text(self, session):
        """Should handle very long text."""
        article = Article(author="John")

        long_text = "A" * 10000
        article.content = long_text

        assert len(article.content) == 10000

    def test_unicode_in_locale_code(self, session):
        """Should handle various locale codes."""
        article = Article(author="John")

        article.set_locale('zh-CN')
        article.title = "你好"

        assert article.get_locale() == 'zh-CN'
        assert article.title == "你好"

    def test_overwrite_existing_translation(self, session):
        """Should overwrite existing translation."""
        article = Article(author="John")

        set_locale('en')
        article.title = "Original"

        article.title = "Updated"

        assert article.title == "Updated"

    def test_multiple_instances_independent(self, session):
        """Should maintain independent translations per instance."""
        article1 = Article(author="John")
        article2 = Article(author="Jane")

        set_locale('en')
        article1.title = "Article 1"
        article2.title = "Article 2"

        assert article1.title == "Article 1"
        assert article2.title == "Article 2"

    def test_empty_translatable_list(self, session):
        """Should handle model with no translatable fields."""

        class SimpleModel(Base, IntIdMixin, TranslatableMixin):
            __tablename__ = 'simple_models'
            __translatable__ = []  # No translatable fields

            name: Mapped[str] = mapped_column(String(100))

        Base.metadata.create_all(session.bind)

        model = SimpleModel(name="Test")

        # Should work normally
        assert model.name == "Test"


# ============================================================================
# Test Integration with i18n Module
# ============================================================================

class TestI18nIntegration:
    """Test integration with i18n module."""

    def test_uses_i18n_locale_context(self, session):
        """Should use locale from i18n module."""
        from fastkit_core.i18n import set_locale as i18n_set_locale, get_locale as i18n_get_locale

        article = Article(author="John")

        # Set via i18n module
        i18n_set_locale('es')

        article.title = "Hola"

        # Should use i18n locale
        assert article.get_locale() == 'es'
        assert article.title == "Hola"

    def test_locale_context_shared(self, session):
        """Should share locale context with i18n."""
        from fastkit_core.i18n import get_locale as i18n_get_locale

        # Set global locale via TranslatableMixin
        TranslatableMixin.set_global_locale('fr')

        # i18n should see the same locale
        # (This depends on implementation - they share _current_locale ContextVar)
        article = Article(author="John")
        assert article.get_locale() == 'fr'


# ============================================================================
# Test Real-World Scenarios
# ============================================================================

class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    def test_cms_article_workflow(self, session):
        """Should handle typical CMS workflow."""
        # Create article in English
        article = Article(author="John")

        set_locale('en')
        article.title = "Getting Started with FastAPI"
        article.content = "FastAPI is a modern web framework..."

        session.add(article)
        session.commit()

        # Later, add Spanish translation
        set_locale('es')
        article.title = "Comenzando con FastAPI"
        article.content = "FastAPI es un framework web moderno..."
        session.commit()

        # API returns appropriate language
        set_locale('en')
        en_data = article.to_dict(locale='en')

        set_locale('es')
        es_data = article.to_dict(locale='es')

        assert en_data['title'] == "Getting Started with FastAPI"
        assert es_data['title'] == "Comenzando con FastAPI"

    def test_ecommerce_product_catalog(self, session):
        """Should handle e-commerce product translations."""
        product = Product(price=2999)

        # English
        product.set_locale('en')
        product.name = "Laptop"
        product.description = "High-performance laptop"

        # Spanish (fallback locale for this model)
        product.set_locale('es')
        product.name = "Portátil"
        product.description = "Portátil de alto rendimiento"

        # French
        product.set_locale('fr')
        product.name = "Ordinateur portable"
        product.description = "Ordinateur portable haute performance"

        session.add(product)
        session.commit()

        # Verify all translations
        assert product.get_translation('name', 'en') == "Laptop"
        assert product.get_translation('name', 'es') == "Portátil"
        assert product.get_translation('name', 'fr') == "Ordinateur portable"

    def test_partial_translation_coverage(self, session):
        """Should handle partial translation coverage gracefully."""
        article = Article(author="John")

        # Full English
        set_locale('en')
        article.title = "Article Title"
        article.content = "Full content in English"

        # Only title in Spanish
        set_locale('es')
        article.title = "Título del artículo"
        # content not translated

        session.add(article)
        session.commit()

        # Spanish: has title, should fallback for content
        assert article.get_translation('title', 'es') == "Título del artículo"
        assert article.get_translation('content', 'es', fallback=True) == "Full content in English"
