"""
Generic Repository Pattern for Database Operations.

Provides common CRUD operations and query helpers.
"""

from __future__ import annotations

from typing import Any, Generic, Type, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fastkit_core.database.base import Base

T = TypeVar('T', bound=Base)


class Repository(Generic[T]):
    """
    Generic repository for database operations.

    Provides common CRUD operations without writing boilerplate.

    Example:
```python
        from fastkit_core.database import Repository
        from sqlalchemy.orm import Session

        # Create repository for User model
        user_repo = Repository(User, session)

        # Create
        user = user_repo.create({'name': 'John', 'email': 'john@test.com'})

        # Read
        user = user_repo.get(1)
        users = user_repo.get_all()
        active_users = user_repo.filter(active=True)

        # Update
        user = user_repo.update(1, {'name': 'Jane'})

        # Delete
        user_repo.delete(1)

        # Pagination
        users, total = user_repo.paginate(page=1, per_page=10)
```
    """

    def __init__(self, model: Type[T], session: Session):
        """
        Initialize repository.

        Args:
            model: SQLAlchemy model class
            session: Database session
        """
        self.model = model
        self.session = session

    # ========================================================================
    # CREATE
    # ========================================================================

    def create(self, data: dict[str, Any], commit: bool = True) -> T:
        """
        Create a new record.

        Args:
            data: Dictionary of attributes
            commit: Whether to commit immediately

        Returns:
            Created model instance

        Example:
```python
            user = repo.create({'name': 'John', 'email': 'john@test.com'})
```
        """
        instance = self.model(**data)
        self.session.add(instance)

        if commit:
            self.session.commit()
            self.session.refresh(instance)

        return instance

    def create_many(
            self,
            data_list: list[dict[str, Any]],
            commit: bool = True
    ) -> list[T]:
        """
        Create multiple records.

        Args:
            data_list: List of attribute dictionaries
            commit: Whether to commit immediately

        Returns:
            List of created instances

        Example:
```python
            users = repo.create_many([
                {'name': 'John', 'email': 'john@test.com'},
                {'name': 'Jane', 'email': 'jane@test.com'}
            ])
```
        """
        instances = [self.model(**data) for data in data_list]
        self.session.add_all(instances)

        if commit:
            self.session.commit()
            for instance in instances:
                self.session.refresh(instance)

        return instances

    # ========================================================================
    # READ
    # ========================================================================

    def get(self, id: Any) -> T | None:
        """
        Get record by ID.

        Args:
            id: Primary key value

        Returns:
            Model instance or None

        Example:
```python
            user = repo.get(1)
```
        """
        return self.session.get(self.model, id)

    def get_or_404(self, id: Any) -> T:
        """
        Get record by ID or raise exception.

        Args:
            id: Primary key value

        Returns:
            Model instance

        Raises:
            ValueError: If record not found
        """
        instance = self.get(id)
        if instance is None:
            raise ValueError(f"{self.model.__name__} with id={id} not found")
        return instance

    def get_all(self, limit: int | None = None) -> list[T]:
        """
        Get all records.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of model instances

        Example:
```python
            all_users = repo.get_all()
            first_100 = repo.get_all(limit=100)
```
        """
        query = select(self.model)

        if limit:
            query = query.limit(limit)

        result = self.session.execute(query)
        return list(result.scalars().all())

    def filter(self, **filters) -> list[T]:
        """
        Filter records by attributes.

        Args:
            **filters: Keyword arguments for filtering

        Returns:
            List of matching instances

        Example:
```python
            active_users = repo.filter(active=True)
            admin_users = repo.filter(role='admin', active=True)
```
        """
        query = select(self.model)

        for key, value in filters.items():
            if hasattr(self.model, key):
                query = query.where(getattr(self.model, key) == value)

        result = self.session.execute(query)
        return list(result.scalars().all())

    def filter_one(self, **filters) -> T | None:
        """
        Get first record matching filters.

        Args:
            **filters: Keyword arguments for filtering

        Returns:
            First matching instance or None

        Example:
```python
            user = repo.filter_one(email='john@test.com')
```
        """
        query = select(self.model)

        for key, value in filters.items():
            if hasattr(self.model, key):
                query = query.where(getattr(self.model, key) == value)

        result = self.session.execute(query.limit(1))
        return result.scalars().first()

    def exists(self, **filters) -> bool:
        """
        Check if record exists.

        Args:
            **filters: Keyword arguments for filtering

        Returns:
            True if exists, False otherwise

        Example:
```python
            exists = repo.exists(email='john@test.com')
```
        """
        return self.filter_one(**filters) is not None

    def count(self, **filters) -> int:
        """
        Count records.

        Args:
            **filters: Optional keyword arguments for filtering

        Returns:
            Number of matching records

        Example:
```python
            total = repo.count()
            active_count = repo.count(active=True)
```
        """
        query = select(func.count()).select_from(self.model)

        for key, value in filters.items():
            if hasattr(self.model, key):
                query = query.where(getattr(self.model, key) == value)

        result = self.session.execute(query)
        return result.scalar() or 0

    # ========================================================================
    # UPDATE
    # ========================================================================

    def update(
            self,
            id: Any,
            data: dict[str, Any],
            commit: bool = True
    ) -> T | None:
        """
        Update record by ID.

        Args:
            id: Primary key value
            data: Dictionary of attributes to update
            commit: Whether to commit immediately

        Returns:
            Updated instance or None if not found

        Example:
```python
            user = repo.update(1, {'name': 'Jane'})
```
        """
        instance = self.get(id)

        if instance is None:
            return None

        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)

        if commit:
            self.session.commit()
            self.session.refresh(instance)

        return instance

    def update_many(
            self,
            filters: dict[str, Any],
            data: dict[str, Any],
            commit: bool = True
    ) -> int:
        """
        Update multiple records matching filters.

        Args:
            filters: Filter conditions
            data: Data to update
            commit: Whether to commit immediately

        Returns:
            Number of updated records

        Example:
```python
            # Deactivate all banned users
            count = repo.update_many(
                filters={'status': 'banned'},
                data={'active': False}
            )
```
        """
        instances = self.filter(**filters)

        for instance in instances:
            for key, value in data.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)

        if commit:
            self.session.commit()

        return len(instances)

    # ========================================================================
    # DELETE
    # ========================================================================

    def delete(self, id: Any, commit: bool = True) -> bool:
        """
        Delete record by ID.

        Args:
            id: Primary key value
            commit: Whether to commit immediately

        Returns:
            True if deleted, False if not found

        Example:
```python
            deleted = repo.delete(1)
```
        """
        instance = self.get(id)

        if instance is None:
            return False

        self.session.delete(instance)

        if commit:
            self.session.commit()

        return True

    def delete_many(
            self,
            filters: dict[str, Any],
            commit: bool = True
    ) -> int:
        """
        Delete multiple records matching filters.

        Args:
            filters: Filter conditions
            commit: Whether to commit immediately

        Returns:
            Number of deleted records

        Example:
```python
            # Delete all inactive users
            count = repo.delete_many({'active': False})
```
        """
        instances = self.filter(**filters)

        for instance in instances:
            self.session.delete(instance)

        if commit:
            self.session.commit()

        return len(instances)

    # ========================================================================
    # PAGINATION
    # ========================================================================

    def paginate(
            self,
            page: int = 1,
            per_page: int = 20,
            **filters
    ) -> tuple[list[T], int]:
        """
        Paginate records.

        Args:
            page: Page number (1-indexed)
            per_page: Items per page
            **filters: Optional filters

        Returns:
            Tuple of (items, total_count)

        Example:
```python
            users, total = repo.paginate(page=2, per_page=10)

            # With filters
            active_users, total = repo.paginate(
                page=1,
                per_page=20,
                active=True
            )
```
        """
        # Build query
        query = select(self.model)

        for key, value in filters.items():
            if hasattr(self.model, key):
                query = query.where(getattr(self.model, key) == value)

        # Get total count
        count_query = select(func.count()).select_from(self.model)
        for key, value in filters.items():
            if hasattr(self.model, key):
                count_query = count_query.where(
                    getattr(self.model, key) == value
                )

        total = self.session.execute(count_query).scalar() or 0

        # Apply pagination
        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)

        # Execute query
        result = self.session.execute(query)
        items = list(result.scalars().all())

        return items, total

    # ========================================================================
    # UTILITY
    # ========================================================================

    def refresh(self, instance: T) -> T:
        """
        Refresh instance from database.

        Args:
            instance: Model instance to refresh

        Returns:
            Refreshed instance
        """
        self.session.refresh(instance)
        return instance

    def commit(self) -> None:
        """Commit current transaction."""
        self.session.commit()

    def rollback(self) -> None:
        """Rollback current transaction."""
        self.session.rollback()

    def flush(self) -> None:
        """Flush pending changes."""
        self.session.flush()


# ============================================================================
# Repository Factory
# ============================================================================

def create_repository(model: Type[T], session: Session) -> Repository[T]:
    """
    Factory function to create repository.

    Args:
        model: SQLAlchemy model class
        session: Database session

    Returns:
        Repository instance

    Example:
```python
        from fastkit_core.database import create_repository

        user_repo = create_repository(User, session)
        post_repo = create_repository(Post, session)
```
    """
    return Repository(model, session)