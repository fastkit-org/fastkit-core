import os

APP_NAME = os.getenv('APP_NAME', '')
DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 't')