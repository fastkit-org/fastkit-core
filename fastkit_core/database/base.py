"""
Base Model with FastKit improvements.

Provides:
- Primary key (id)
- Dict/JSON serialization with relationships
- Query helpers
- Auto-generated table names
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, TypeVar

from sqlalchemy.orm import DeclarativeBase, declared_attr

T = TypeVar('T', bound='Base')


class Base(DeclarativeBase):
    """
    Base model for all FastKit models.

    Provides common functionality:
    - Dict serialization with relationship support
    - JSON export
    - Auto-generated table names

    Example:
```python
        from fastkit_core.database import Base
        from sqlalchemy import String

        class User(Base):
            # __tablename__ is auto-generated as 'users'
            name: Mapped[str] = mapped_column(String(100))
            email: Mapped[str] = mapped_column(String(255), unique=True)

        # Auto-included: id
```
    """

    # Don't create table for Base itself
    __abstract__ = True

    # Auto-generate table name from class name
    @declared_attr
    def __tablename__(cls) -> str:
        """
        Auto-generate table name from class name.

        Converts CamelCase to snake_case and pluralizes.
        Examples:
            User -> users
            UserProfile -> user_profiles
            Category -> categories
        """
        if hasattr(cls, '__tablename_override__'):
            return cls.__tablename_override__

        # Convert CamelCase to snake_case
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', cls.__name__)
        name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()

        # Simple pluralization (English)
        if name.endswith('y') and name[-2] not in 'aeiou':
            name = name[:-1] + 'ies'
        elif name.endswith('s') or name.endswith('x') or name.endswith('z'):
            name = name + 'es'
        elif name.endswith('ch') or name.endswith('sh'):
            name = name + 'es'
        else:
            name = name + 's'

        return name


    # ========================================================================
    # Serialization
    # ========================================================================

    def to_dict(
        self,
        exclude: list[str] | None = None,
        include_relationships: bool = False,
        max_depth: int = 1,
        locale: str | None = None,
        _current_depth: int = 0
    ) -> dict[str, Any]:
        """
        Convert model to dictionary.

        Args:
            exclude: List of field names to exclude
            include_relationships: Include related objects
            max_depth: Maximum depth for nested relationships (prevents infinite recursion)
            locale: Get values of specific language
            _current_depth: Internal tracker for recursion depth

        Returns:
            Dictionary representation

        Example:
```python
            user = User.query.first()

            # Simple dict
            data = user.to_dict(exclude=['password'])
            # {'id': 1, 'name': 'John', 'email': 'john@test.com', ...}

            # With relationships
            data = user.to_dict(include_relationships=True)
            # {'id': 1, 'name': 'John', 'posts': [...], ...}
```
        """
        from sqlalchemy import inspect as sa_inspect

        exclude = exclude or []
        result = {}

        is_translatable = hasattr(self, '__translatable__')
        translatable_fields = getattr(self, '__translatable__', [])

        # Columns
        for column in sa_inspect(self).mapper.column_attrs:
            key = column.key
            if key not in exclude:
                value = getattr(self, key)

                if is_translatable and key in translatable_fields:
                    if locale:
                        # Get specific locale translation
                        value = self.get_translation(key, locale, fallback=True)

                # Handle datetime serialization
                if isinstance(value, datetime):
                    value = value.isoformat()

                result[key] = value

        # Relationships
        if include_relationships and _current_depth < max_depth:
            for relationship in sa_inspect(self).mapper.relationships:
                key = relationship.key
                if key not in exclude:
                    related = getattr(self, key, None)

                    if related is None:
                        result[key] = None
                    elif isinstance(related, list):
                        # One-to-many or many-to-many
                        result[key] = [
                            item.to_dict(
                                exclude=exclude,
                                include_relationships=True,
                                max_depth=max_depth,
                                _current_depth=_current_depth + 1
                            )
                            for item in related
                        ]
                    else:
                        # Many-to-one or one-to-one
                        result[key] = related.to_dict(
                            exclude=exclude,
                            include_relationships=True,
                            max_depth=max_depth,
                            _current_depth=_current_depth + 1
                        )

        return result

    def to_json(
        self,
        exclude: list[str] | None = None,
        include_relationships: bool = False
    ) -> dict[str, Any]:
        """
        Alias for to_dict() (more intuitive for API responses).
        """
        return self.to_dict(
            exclude=exclude,
            include_relationships=include_relationships
        )

    def update_from_dict(
        self,
        data: dict[str, Any],
        exclude: list[str] | None = None,
        allow_only: list[str] | None = None
    ) -> None:
        """
        Update model attributes from dictionary.

        Args:
            data: Dictionary of attributes to update
            exclude: List of attributes to exclude from update

        Example:
```python
            user = User.query.first()
            user.update_from_dict({
                'name': 'Jane',
                'email': 'jane@test.com'
            })
            session.commit()
```
        """
        if allow_only:
            data = {k: v for k, v in data.items() if k in allow_only}

        exclude = exclude or []

        for key, value in data.items():
            # Skip excluded fields
            if key in exclude:
                continue

            # Skip non-existent attributes
            if not hasattr(self, key):
                continue

            # Skip primary key and timestamps (unless explicitly needed)
            if key in ('id'):
                continue

            setattr(self, key, value)

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def __repr__(self) -> str:
        """String representation."""
        attrs = self.__repr_attrs__()

        if attrs:
            attrs_str = ', '.join(f"{k}={v!r}" for k, v in attrs)
            return f"<{self.__class__.__name__}({attrs_str})>"

        return f"<{self.__class__.__name__}(id={self.id})>"

    def __repr_attrs__(self) -> list[tuple[str, Any]]:
        """
        Override this to customize repr output.

        Returns:
            List of (key, value) tuples to include in repr

        Example:
```python
            class User(Base):
                name: Mapped[str]

                def __repr_attrs__(self):
                    return [('id', self.id), ('name', self.name)]
```
        """
        return [('id', self.id)]