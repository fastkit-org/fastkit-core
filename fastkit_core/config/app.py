import os

APP_NAME = os.getenv('APP_NAME', '')
DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 't')
DEFAULT_LANGUAGE = os.getenv('DEFAULT_LANGUAGE', 'en')
FALLBACK_LANGUAGE = os.getenv('FALLBACK_LANGUAGE', 'en')
TRANSLATIONS_PATH = os.getenv('TRANSLATIONS_PATH', 'translations')