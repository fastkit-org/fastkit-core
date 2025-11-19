"""
Base Model with FastKit improvements.

Provides:
- Automatic timestamps (created_at, updated_at)
- Primary key (id)
- Dict/JSON serialization
- Query helpers
- Repository access
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, TypeVar

from sqlalchemy import inspect
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

T = TypeVar('T', bound='Base')


class Base(DeclarativeBase):
    """
    Base model for all FastKit models.

    Provides common functionality:
    - Auto-incrementing ID
    - Timestamps (created_at, updated_at)
    - Dict serialization
    - JSON export

    Example:
```python
        from fastkit_core.database import Base
        from sqlalchemy import Column, String

        class User(Base):
            __tablename__ = "users"

            name: Mapped[str] = mapped_column(String(100))
            email: Mapped[str] = mapped_column(String(255), unique=True)

        # Auto-included: id, created_at, updated_at
```
    """

    # Don't create table for Base itself
    __abstract__ = True

    # Primary key (auto-incrementing)
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Timestamps (automatically managed)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # ========================================================================
    # Serialization
    # ========================================================================

    def to_dict(self, exclude: list[str] | None = None) -> dict[str, Any]:
        """
        Convert model to dictionary.

        Args:
            exclude: List of field names to exclude

        Returns:
            Dictionary representation

        Example:
```python
            user = User.query.first()
            data = user.to_dict(exclude=['password'])
            # {'id': 1, 'name': 'John', 'email': 'john@test.com', ...}
```
        """
        exclude = exclude or []

        result = {}
        for column in inspect(self).mapper.column_attrs:
            key = column.key
            if key not in exclude:
                value = getattr(self, key)

                # Handle datetime serialization
                if isinstance(value, datetime):
                    value = value.isoformat()

                result[key] = value

        return result

    def to_json(self, exclude: list[str] | None = None) -> dict[str, Any]:
        """
        Alias for to_dict() (more intuitive for API responses).
        """
        return self.to_dict(exclude=exclude)

    def update_from_dict(self, data: dict[str, Any]) -> None:
        """
        Update model attributes from dictionary.

        Args:
            data: Dictionary of attributes to update

        Example:
```python
            user = User.query.first()
            user.update_from_dict({'name': 'Jane', 'email': 'jane@test.com'})
            session.commit()
```
        """
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def __repr__(self) -> str:
        """String representation."""
        return f"<{self.__class__.__name__}(id={self.id})>"

    @classmethod
    def __tablename_from_class__(cls) -> str:
        """
        Generate table name from class name.

        Converts CamelCase to snake_case and pluralizes.
        UserProfile -> user_profiles
        """
        import re

        # Convert CamelCase to snake_case
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', cls.__name__)
        name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()

        # Simple pluralization (English)
        if name.endswith('y'):
            name = name[:-1] + 'ies'
        elif name.endswith('s'):
            name = name + 'es'
        else:
            name = name + 's'

        return name