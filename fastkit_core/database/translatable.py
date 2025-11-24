from contextvars import ContextVar
from typing import Any
from sqlalchemy import event
import json
from fastkit_core.config import ConfigManager

config = ConfigManager(modules=['app'], config_package='fastkit_core.config')
_current_locale: ContextVar[str] = ContextVar('locale', default=config.get('app.DEFAULT_LANGUAGE'))

class TranslatableMixin:
    """
    Automatic multi-language support with zero boilerplate.

    Features:
    - Auto-converts string fields to JSON storage
    - Transparent get/set (works like normal strings)
    - Context-aware locale (from request or manual)
    - Partial updates (update one language, keep others)
    - Fallback to default locale

    Example:
        class Article(Base, TranslatableMixin, TimestampMixin):
            __translatable__ = ['title', 'content']
            __fallback_locale__ = 'en'

            title: Mapped[str]  # Clean! No JSON type needed
            content: Mapped[str]
            author: Mapped[str]  # Not translatable

        # Usage
        article = Article()
        article.title = "Hello World"  # Saves to current locale (en)

        article.set_locale('es')
        article.title = "Hola Mundo"  # Saves to Spanish

        article.set_locale('en')
        print(article.title)  # "Hello World"

        # Get all translations
        print(article.get_translations('title'))
        # {'en': 'Hello World', 'es': 'Hola Mundo'}
    """

    # Configure in your model
    __translatable__: list[str] = []
    __fallback_locale__: str = config.get('app.DEFAULT_LANGUAGE')

    def get_locale(self) -> str:
        """Get current locale for this instance."""
        if hasattr(self, '_instance_locale'):
            return self._instance_locale
        return _current_locale.get()

    def set_locale(self, locale: str) -> 'TranslatableMixin':
        """Set locale for this instance. Returns self for chaining."""
        self._instance_locale = locale
        return self

    @classmethod
    def set_global_locale(cls, locale: str) -> None:
        """Set global locale (affects all instances)."""
        _current_locale.set(locale)

    @classmethod
    def get_global_locale(cls) -> str:
        """Get current global locale."""
        return _current_locale.get()

    def get_translations(self, field: str) -> dict[str, str]:
        """
        Get all translations for a field.

        Returns:
            Dict mapping locale codes to translated values
            Example: {'en': 'Hello', 'es': 'Hola', 'fr': 'Bonjour'}
        """
        if field not in self.__translatable__:
            raise ValueError(f"Field '{field}' is not translatable")

        storage_name = f'_translatable_{field}'
        return getattr(self, storage_name, {}).copy()

    def set_translation(
            self,
            field: str,
            value: str,
            locale: str = None
    ) -> 'TranslatableMixin':
        """
        Set translation for specific locale explicitly.

        Args:
            field: Field name
            value: Translated value
            locale: Locale code (e.g., 'en', 'es')

        Returns:
            Self for chaining
        """
        if field not in self.__translatable__:
            raise ValueError(f"Field '{field}' is not translatable")

        if locale is None:
            locale = self.get_locale()

        storage_name = f'_translatable_{field}'
        translations = getattr(self, storage_name, None)
        if translations is None:
            translations = {}
            setattr(self, storage_name, translations)

        translations[locale] = value

        # Mark as modified
        from sqlalchemy.orm import attributes
        attributes.flag_modified(self, field)

        return self