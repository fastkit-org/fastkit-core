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
from typing import Any, Optional
from contextvars import ContextVar

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
            print(f"Warning: Translations directory not found: {self.translations_dir}")
            return

        for file in self.translations_dir.glob('*.json'):
            locale = file.stem
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    self._translations[locale] = json.load(f)
            except json.JSONDecodeError as e:
                print(f"Error loading {file}: {e}")
            except Exception as e:
                print(f"Error reading {file}: {e}")
