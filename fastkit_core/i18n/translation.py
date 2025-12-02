"""
Translation Manager - Load and manage translations from JSON files.

Provides Laravel-style translation helpers with:
- Dot notation access (messages.welcome)
- Variable replacement ({name})
- Pluralization support
- Locale fallback
- Integration with TranslatableMixin
"""

import json
from pathlib import Path
from typing import Any
from contextvars import ContextVar
import logging
logger = logging.getLogger(__name__)

# Shared locale context with TranslatableMixin
try:
    from fastkit_core.database.translatable import _current_locale
except ImportError:
    _current_locale: ContextVar[str | None] = ContextVar('locale', default=None)


class TranslationManager:
    """
    Manages translations from JSON files.

    File structure:
        translations/
        ├── en.json
        ├── es.json
        └── fr.json

    JSON structure:
        {
            "messages": {
                "welcome": "Welcome, {name}!",
                "goodbye": "Goodbye!"
            },
            "items": {
                "count": "{count} item|{count} items"
            }
        }

    Usage:
        manager = TranslationManager()
        text = manager.get('messages.welcome', name='John')
        # "Welcome, John!"

        # Or use helper
        text = t('messages.welcome', name='John')
    """

    def __init__(self, translations_dir: str | Path | None = None):
        """
        Initialize translation manager.

        Args:
            translations_dir: Path to translations directory.
                            If None, uses config value.
        """
        from fastkit_core.config import get_config_manager

        config = get_config_manager()

        # Get translations directory
        if translations_dir is None:
            translations_dir = config.get('app.TRANSLATIONS_PATH', 'translations')

        self.translations_dir = Path(translations_dir)
        self.default_locale = config.get('app.DEFAULT_LANGUAGE', 'en')
        self.fallback_locale = config.get('app.FALLBACK_LANGUAGE', 'en')

        # Load all translations
        self._translations: dict[str, dict] = {}
        self._load_translations()

    def _load_translations(self) -> None:
        """Load all translation files from directory."""
        if not self.translations_dir.exists():
            return

        for file in self.translations_dir.glob('*.json'):
            locale = file.stem
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    self._translations[locale] = json.load(f)
            except json.JSONDecodeError as e:
                logger.warning(f"Error loading {file}: {e}")
            except Exception as e:
                logger.warning(f"Error reading {file}: {e}")

    def get(
            self,
            key: str,
            locale: str | None = None,
            fallback: bool = True,
            **replacements
    ) -> str:
        """
        Get translation for a key.

        Args:
            key: Translation key in dot notation (e.g., 'messages.welcome')
            locale: Locale code. If None, uses current context locale.
            fallback: If True, fallback to default locale if key not found
            **replacements: Variables to replace in translation string

        Returns:
            Translated string or the key if not found

        Example:
            t('messages.welcome', name='John')
            # "Welcome, John!"

            t('messages.items', count=5)
            # "5 items"
        """
        # Determine locale
        if locale is None:
            # Try to get from context (shared with TranslatableMixin)
            locale = _current_locale.get()
            if locale is None:
                locale = self.default_locale

        # Get translation data for locale
        locale_data = self._translations.get(locale)

        # If locale not found and fallback enabled, try fallback locale
        if locale_data is None and fallback and locale != self.fallback_locale:
            locale_data = self._translations.get(self.fallback_locale)

        # If still not found, return key
        if locale_data is None:
            return key

        # Navigate through nested keys
        value = self._get_nested_value(locale_data, key)

        # If not found and fallback enabled, try fallback locale
        if value is None and fallback and locale != self.fallback_locale:
            fallback_data = self._translations.get(self.fallback_locale)
            if fallback_data:
                value = self._get_nested_value(fallback_data, key)

        # If still not found, return key
        if value is None:
            return key

        # Replace variables
        if isinstance(value, str) and replacements:
            value = self._replace_variables(value, replacements)

        return value if isinstance(value, str) else key

    def _get_nested_value(self, data: dict, key: str) -> Any:
        """
        Get value from nested dict using dot notation.

        Args:
            data: Dictionary to search
            key: Dot-separated key (e.g., 'messages.welcome')

        Returns:
            Value if found, None otherwise
        """
        keys = key.split('.')
        current = data

        for part in keys:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None

        return current

    def _replace_variables(self, text: str, replacements: dict) -> str:
        """
        Replace {variable} placeholders in text.

        Args:
            text: Text with placeholders
            replacements: Dict of variable values

        Returns:
            Text with replacements applied
        """
        try:
            return text.format(**replacements)
        except KeyError as e:
            # If variable not found, leave placeholder
            logger.warning(f"Warning: Missing translation variable: {e}")
            return text
        except Exception as e:
            logger.warning(f"Error replacing variables: {e}")
            return text

    def has(self, key: str, locale: str | None = None) -> bool:
        """
        Check if translation key exists.

        Args:
            key: Translation key
            locale: Locale code

        Returns:
            True if key exists, False otherwise
        """
        if locale is None:
            locale = _current_locale.get() or self.default_locale

        locale_data = self._translations.get(locale)
        if locale_data is None:
            return False

        return self._get_nested_value(locale_data, key) is not None

    def get_locale(self) -> str:
        """Get current locale from context."""
        return _current_locale.get() or self.default_locale

    def set_locale(self, locale: str) -> None:
        """Set locale in context (shared with TranslatableMixin)."""
        _current_locale.set(locale)

    def reload(self) -> None:
        """Reload all translation files."""
        self._translations.clear()
        self._load_translations()

    def get_all(self, locale: str | None = None) -> dict:
        """
        Get all translations for a locale.

        Args:
            locale: Locale code. If None, uses current locale.

        Returns:
            Dictionary of all translations
        """
        if locale is None:
            locale = self.get_locale()

        return self._translations.get(locale, {})

    def get_available_locales(self) -> list[str]:
        """Get list of available locale codes."""
        return list(self._translations.keys())


# ============================================================================
# Global Instance & Helper Functions
# ============================================================================

_translation_manager: TranslationManager | None = None


def get_translation_manager() -> TranslationManager:
    """
    Get global translation manager instance.

    Creates one if it doesn't exist.

    Returns:
        Global TranslationManager instance
    """
    global _translation_manager

    if _translation_manager is None:
        _translation_manager = TranslationManager()

    return _translation_manager


def set_translation_manager(manager: TranslationManager) -> None:
    """
    Set global translation manager.

    Useful for testing or custom configuration.

    Args:
        manager: TranslationManager instance
    """
    global _translation_manager
    _translation_manager = manager


def _(key: str, locale: str | None = None, **replacements) -> str:
    """
    Translate a key (helper function).

    Args:
        key: Translation key in dot notation
        locale: Optional locale override
        **replacements: Variables to replace

    Returns:
        Translated string

    Example:
        # Simple translation
        _('messages.welcome')
        # "Welcome!"

        # With variables
        _('messages.hello', name='John')
        # "Hello, John!"

        # With pluralization
        _('messages.items', count=5)
        # "5 items"

        # With specific locale
        _('messages.welcome', locale='es')
        # "¡Bienvenido!"
    """
    manager = get_translation_manager()
    return manager.get(key, locale=locale, **replacements)

def gettext(key: str, locale: str | None = None, **replacements) -> str:
    return _(key, locale, **replacements)

def set_locale(locale: str) -> None:
    """
    Set current locale.

    Args:
        locale: Locale code (e.g., 'en', 'es', 'fr')
    """
    manager = get_translation_manager()
    manager.set_locale(locale)


def get_locale() -> str:
    """
    Get current locale.

    Returns:
        Current locale code
    """
    manager = get_translation_manager()
    return manager.get_locale()

__all__ = [
    'TranslationManager',
    'get_translation_manager',
    'set_translation_manager',
    '_',
    'gettext',
    'set_locale',
    'get_locale',
]
