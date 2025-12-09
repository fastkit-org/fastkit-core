"""
Generic Repository Pattern for Database Operations.

Provides common CRUD operations and query helpers.
"""

from __future__ import annotations

from typing import Any, Generic, Type, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

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

    LOOKUP_OPERATORS = {
        'eq': lambda col, val: col == val,  # Equal (default)
        'ne': lambda col, val: col != val,  # Not equal
        'lt': lambda col, val: col < val,  # Less than
        'lte': lambda col, val: col <= val,  # Less than or equal
        'gt': lambda col, val: col > val,  # Greater than
        'gte': lambda col, val: col >= val,  # Greater than or equal
        'in': lambda col, val: col.in_(val),  # IN (list)
        'not_in': lambda col, val: col.not_in(val),  # NOT IN
        'like': lambda col, val: col.like(val),  # LIKE
        'ilike': lambda col, val: col.ilike(val),  # Case-insensitive LIKE
        'is_null': lambda col, val: col.is_(None) if val else col.isnot(None),
        'is_not_null': lambda col, val: col.isnot(None),
        'between': lambda col, val: col.between(val[0], val[1]),  # BETWEEN
        'startswith': lambda col, val: col.like(f'{val}%'),
        'endswith': lambda col, val: col.like(f'%{val}'),
        'contains': lambda col, val: col.like(f'%{val}%'),
    }

    def __init__(self, model: Type[T], session: Session):
        """
        Initialize repository.

        Args:
            model: SQLAlchemy model class
            session: Database session
        """
        self.model = model
        self.session = session

    def _has_soft_delete(self) -> bool:
        """Check if model has soft delete support."""
        return hasattr(self.model, 'deleted_at')

    def query(self):
        """Get query builder for complex queries."""
        return select(self.model)

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
        Get record by primary key.

        Excludes soft-deleted records by default.

        Args:
            id: Primary key value

        Returns:
            Model instance or None if not found or soft-deleted
        """
        query = select(self.model).where(self.model.id == id)

        # Exclude soft-deleted records
        if self._has_soft_delete():
            query = query.where(self.model.deleted_at.is_(None))

        result = self.session.execute(query)
        return result.scalar_one_or_none()

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

        if self._has_soft_delete():
            query = query.where(self.model.deleted_at.is_(None))

        if limit:
            query = query.limit(limit)

        result = self.session.execute(query)
        return list(result.scalars().all())

    def filter(
            self,
            _limit: int | None = None,
            _offset: int | None = None,
            _order_by: str | None = None,
            **filters
    ) -> list[T]:
        """
        Filter records with operator support.

        Supports Django-style field lookups:
        - field__operator=value

        Operators:
        - eq: Equal (default if no operator)
        - ne: Not equal
        - lt, lte, gt, gte: Comparisons
        - in, not_in: IN/NOT IN lists
        - like, ilike: LIKE patterns
        - is_null: IS NULL (pass True/False)
        - is_not_null: IS NOT NULL (pass True/False)
        - between: BETWEEN (pass tuple/list of 2 values)
        - startswith, endswith, contains: String patterns

        Examples:
            # Simple equality (no operator needed)
            repo.filter(status='active')

            # With operators
            repo.filter(age__gte=18, age__lt=65)
            repo.filter(email__ilike='%@gmail.com')
            repo.filter(status__in=['active', 'pending'])
            repo.filter(deleted_at__is_null=True)
            repo.filter(price__between=(10, 100))
            repo.filter(name__startswith='John')

            # With pagination
            repo.filter(status='active', _limit=10, _offset=20)

            # With ordering
            repo.filter(age__gte=18, _order_by='name')  # ASC
            repo.filter(age__gte=18, _order_by='-created_at')  # DESC
        """
        query = select(self.model)

        if self._has_soft_delete():
            query = query.where(self.model.deleted_at.is_(None))

        # Build WHERE conditions
        conditions = []
        for key, value in filters.items():
           self._parse_field_operator(key, value, conditions)

        # Apply all conditions
        if conditions:
            query = query.where(and_(*conditions))

        # Apply ordering
        if _order_by:
            if _order_by.startswith('-'):
                # Descending order
                field = _order_by[1:]
                if hasattr(self.model, field):
                    query = query.order_by(getattr(self.model, field).desc())
            else:
                # Ascending order
                if hasattr(self.model, _order_by):
                    query = query.order_by(getattr(self.model, _order_by))

        # Apply limit and offset
        if _offset:
            query = query.offset(_offset)
        if _limit:
            query = query.limit(_limit)

        # Execute
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
        results = self.filter(_limit=1, **filters)
        return results[0] if results else None

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

    def filter_or(self, *filter_groups, **and_filters) -> list[T]:
        """
        Filter with OR conditions.

        Example:
            # (status='active' OR status='pending') AND age >= 18
            users = repo.filter_or(
                {'status': 'active'},
                {'status': 'pending'},
                age__gte=18
            )
        """
        query = select(self.model)

        if self._has_soft_delete():
            query = query.where(self.model.deleted_at.is_(None))

        # OR conditions
        if filter_groups:
            or_conditions = []
            for group in filter_groups:
                group_conditions = []
                for key, value in group.items():
                    self._parse_field_operator(key, value, group_conditions)
                if group_conditions:
                    or_conditions.append(and_(*group_conditions))

            if or_conditions:
                query = query.where(or_(*or_conditions))

        # AND conditions
        # (same as filter())

        result = self.session.execute(query)
        return list(result.scalars().all())

    def count(self, **filters) -> int:
        """
        Count records with operator support.

        Args:
            **filters: Keyword arguments for filtering (supports operators)

        Returns:
            Number of matching records

        Example:
    ```python
            total = repo.count()
            adult_count = repo.count(age__gte=18)
            active_count = repo.count(status='active', deleted_at__is_null=True)
    ```
        """
        query = select(func.count()).select_from(self.model)

        if self._has_soft_delete():
            query = query.where(self.model.deleted_at.is_(None))

        # Build WHERE conditions using operator support
        conditions = []
        for key, value in filters.items():
            self._parse_field_operator(key, value, conditions)

        if conditions:
            query = query.where(and_(*conditions))

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

    def delete(self, id: Any, commit: bool = True, force: bool = False) -> bool:
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
        :param id:
        :param commit:
        :param force:
        """
        instance = self.get(id)

        if instance is None:
            return False

        if hasattr(instance, 'soft_delete') and not force:
            instance.soft_delete()
        else:
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
            _order_by: str | None = None,
            **filters
    ) -> tuple[list[T], dict[str, Any]]:
        """
        Paginate records with metadata.

        Excludes soft-deleted records by default.

        Args:
            page: Page number (1-indexed)
            per_page: Items per page
            _order_by: Order by field (prefix with - for DESC)
            **filters: Filter conditions with operators

        Returns:
            Tuple of (items, metadata)

        Example:
            # Page 2, 20 items per page, sorted by created_at descending
            users, meta = repo.paginate(
                page=2,
                per_page=20,
                _order_by='-created_at',
                is_active=True
            )
        """
        # Get total count (with filters)
        total = self.count(**filters)

        # Calculate pagination metadata
        total_pages = (total + per_page - 1) // per_page if total > 0 else 0
        offset = (page - 1) * per_page

        # Get items with limit, offset, and ordering
        items = self.filter(
            _limit=per_page,
            _offset=offset,
            _order_by=_order_by,
            **filters
        )

        # Build metadata
        metadata = {
            'page': page,
            'per_page': per_page,
            'total': total,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1
        }

        return items, metadata

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

    def _parse_field_operator(self, key: str, value: Any, conditions: list[Any]):
        # Parse field__operator format
        if '__' in key:
            field_name, operator = key.rsplit('__', 1)
        else:
            field_name = key
            operator = 'eq'  # Default to equality

        # Validate field exists on model
        if not hasattr(self.model, field_name):
            raise ValueError(
                f"Field '{field_name}' does not exist on {self.model.__name__}"
            )

        # Validate operator
        if operator not in self.LOOKUP_OPERATORS:
            raise ValueError(
                f"Unknown operator '{operator}'. "
                f"Available: {', '.join(self.LOOKUP_OPERATORS.keys())}"
            )

        # Get column and apply operator
        column = getattr(self.model, field_name)
        condition = self.LOOKUP_OPERATORS[operator](column, value)
        conditions.append(condition)


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