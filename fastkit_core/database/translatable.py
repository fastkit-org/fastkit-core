from contextvars import ContextVar
from typing import Any
from sqlalchemy import event
import json
from fastkit_core.config import ConfigManager

config = ConfigManager(modules=['app'], config_package='fastkit_core.config')
_current_locale: ContextVar[str] = config.get('app.DEFAULT_LANGUAGE')


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