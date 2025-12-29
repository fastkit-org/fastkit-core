"""
FastKit Database Module

Provides:
- Base model with timestamps and serialization
- Useful mixins (UUID, SoftDelete, Timestamps, Slug, Publishable, etc.)
- Session management with read/write replica support
- Connection manager for multiple databases
- Generic repository pattern
- FastAPI integration

Example:
```python
    from fastkit_core.database import (
        Base,
        DatabaseManager,
        Repository,
        init_database,
        get_db,
        # Mixins
        UUIDMixin,
        SoftDeleteMixin,
        SlugMixin,
        PublishableMixin,
    )

    # Define model
    class User(Base, SoftDeleteMixin):
        name: Mapped[str]
        email: Mapped[str]

    # Initialize database
    config = ConfigManager()
    db = DatabaseManager(config)

    # Use repository
    with db.session() as session:
        user_repo = Repository(User, session)
        user = user_repo.create({'name': 'John', 'email': 'john@test.com'})
```
"""

from fastkit_core.database.base import Base
from fastkit_core.database.base_with_timestamps import BaseWithTimestamps
from fastkit_core.database.manager import (
    ConnectionManager,
    get_connection_manager,
    set_connection_manager,
)
from fastkit_core.database.mixins import (
    PublishableMixin,
    SlugMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDMixin,
    IntIdMixin,
)
from fastkit_core.database.repository import Repository, create_repository
from fastkit_core.database.session import (
    DatabaseManager,
    get_db,
    get_db_manager,
    get_read_db,
    health_check_all,
    init_database,
    shutdown_database,
    build_database_url
)

from fastkit_core.database.translatable import TranslatableMixin, set_locale_from_request

__all__ = [
    # Base
    'Base',
    # Session Management
    'DatabaseManager',
    'init_database',
    'get_db_manager',
    'get_db',
    'get_read_db',
    'shutdown_database',
    'health_check_all',
    'build_database_url',
    # Connection Manager
    'ConnectionManager',
    'get_connection_manager',
    'set_connection_manager',
    # Repository
    'Repository',
    'create_repository',
    # Mixins
    'IntIdMixin',
    'UUIDMixin',
    'SoftDeleteMixin',
    'TimestampMixin',
    'SlugMixin',
    'PublishableMixin',
    'BaseWithTimestamps',
    # Translations
    'TranslatableMixin',
    'set_locale_from_request',
]