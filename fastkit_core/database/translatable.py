from contextvars import ContextVar
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

    def get_translation(
            self,
            field: str,
            locale: str = None,
            fallback: bool = True
    ) -> str | None:
        """
        Get translation for specific locale explicitly.

        Args:
            field: Field name
            locale: Locale code
            fallback: If True, fallback to default locale if not found

        Returns:
            Translated value or None
        """
        if field not in self.__translatable__:
            raise ValueError(f"Field '{field}' is not translatable")

        translations = self.get_translations(field)

        if locale is None:
            locale = self.get_locale()

        # Try requested locale
        if locale in translations:
            return translations[locale]

        # Fallback
        if fallback and locale != self.__fallback_locale__:
            return translations.get(self.__fallback_locale__)

        return None

    def has_translation(self, field: str, locale: str) -> bool:
        """Check if translation exists for field in specific locale."""
        if field not in self.__translatable__:
            return False
        translations = self.get_translations(field)
        return locale in translations


# SQLAlchemy event listeners
@event.listens_for(TranslatableMixin, 'load', propagate=True)
def deserialize_translations(target, context):
    """After loading from DB, parse JSON into internal storage."""
    for field in target.__translatable__:
        # Get raw value from column
        raw_value = object.__getattribute__(target, field)
        storage_name = f'_translatable_{field}'

        if raw_value:
            if isinstance(raw_value, dict):
                # Already a dict (JSON was auto-parsed)
                setattr(target, storage_name, raw_value)
            elif isinstance(raw_value, str):
                # Need to parse JSON string
                try:
                    translations = json.loads(raw_value)
                    setattr(target, storage_name, translations)
                except json.JSONDecodeError:
                    # Not valid JSON, treat as single translation
                    setattr(target, storage_name, {
                        target.__fallback_locale__: raw_value
                    })
        else:
            setattr(target, storage_name, {})


@event.listens_for(TranslatableMixin, 'before_insert', propagate=True)
@event.listens_for(TranslatableMixin, 'before_update', propagate=True)
def serialize_translations(mapper, connection, target):
    """Before saving to DB, convert internal storage to JSON."""
    for field in target.__translatable__:
        storage_name = f'_translatable_{field}'
        translations = getattr(target, storage_name, {})

        # Set the actual column value to the dict
        # SQLAlchemy will handle JSON serialization
        setattr(target, field, translations if translations else None)