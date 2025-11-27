"""
FastKit Translations Module

Provides Laravel-style translation management from JSON files.
"""

from fastkit_core.i18n.translation import (
    TranslationManager,
    get_translation_manager,
    set_translation_manager,
    _,
    gettext,
    set_locale,
    get_locale
)


__all__ = [
    'TranslationManager',
    'get_translation_manager',
    'set_translation_manager',
    '_',
    'gettext',
    'set_locale',
    'get_locale',
]