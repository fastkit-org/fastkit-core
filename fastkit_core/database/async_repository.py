"""
Async Generic Repository Pattern for Database Operations.

Provides common CRUD operations and query helpers for async SQLAlchemy.
Full feature parity with sync Repository.
"""

from __future__ import annotations

from typing import Any, Generic, Type, TypeVar, Optional, List

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from fastkit_core.database.base import Base

T = TypeVar('T', bound=Base)


class AsyncRepository(Generic[T]):
    """
    Async generic repository for database operations.

    Provides common CRUD operations without writing boilerplate.
    Full async/await support with feature parity to sync Repository.

    Example:
    ```python
        from fastkit_core.database import AsyncRepository
        from sqlalchemy.ext.asyncio import AsyncSession

        # Create repository for User model
        user_repo = AsyncRepository(User, session)

        # Create
        user = await user_repo.create({'name': 'John', 'email': 'john@test.com'})

        # Read
        user = await user_repo.get(1)
        users = await user_repo.get_all()
        active_users = await user_repo.filter(active=True)

        # Update
        user = await user_repo.update(1, {'name': 'Jane'})

        # Delete
        await user_repo.delete(1)

        # Pagination
        users, meta = await user_repo.paginate(page=1, per_page=10)
    ```
    """

    LOOKUP_OPERATORS = {
        'eq': lambda col, val: col == val,
        'ne': lambda col, val: col != val,
        'lt': lambda col, val: col < val,
        'lte': lambda col, val: col <= val,
        'gt': lambda col, val: col > val,
        'gte': lambda col, val: col >= val,
        'in': lambda col, val: col.in_(val),
        'not_in': lambda col, val: col.not_in(val),
        'like': lambda col, val: col.like(val),
        'ilike': lambda col, val: col.ilike(val),
        'is_null': lambda col, val: col.is_(None) if val else col.isnot(None),
        'is_not_null': lambda col, val: col.isnot(None),
        'between': lambda col, val: col.between(val[0], val[1]),
        'startswith': lambda col, val: col.like(f'{val}%'),
        'endswith': lambda col, val: col.like(f'%{val}'),
        'contains': lambda col, val: col.like(f'%{val}%'),
    }

    def __init__(self, model: Type[T], session: AsyncSession):
        """
        Initialize async repository.

        Args:
            model: SQLAlchemy model class
            session: Async database session
        """
        self.model = model
        self.session = session

    def _has_soft_delete(self) -> bool:
        """Check if model has soft delete support."""
        return hasattr(self.model, 'deleted_at')

    def _apply_eager_loading(
            self,
            stmt,
            load: Optional[List[str]] = None,
            load_strategy: str = 'selectin'
    ):
        """Apply eager loading to statement."""
        if not load:
            return stmt

        loader = selectinload if load_strategy == 'selectin' else joinedload

        for relationship_path in load:
            parts = relationship_path.split('.')
            current_loader = loader(getattr(self.model, parts[0]))

            for part in parts[1:]:
                current_loader = current_loader.selectinload(part)

            stmt = stmt.options(current_loader)

        return stmt

    def query(self):
        """Get query builder for complex queries."""
        return select(self.model)

    # ========================================================================
    # CREATE
    # ========================================================================

    async def create(self, data: dict[str, Any], commit: bool = True) -> T:
        """
        Create a new record asynchronously.

        Args:
            data: Dictionary of attributes
            commit: Whether to commit immediately

        Returns:
            Created model instance

        Example:
        ```python
            user = await repo.create({'name': 'John', 'email': 'john@test.com'})
        ```
        """
        instance = self.model(**data)
        self.session.add(instance)

        if commit:
            await self.session.commit()
            await self.session.refresh(instance)

        return instance

    async def create_many(
            self,
            data_list: list[dict[str, Any]],
            commit: bool = True
    ) -> list[T]:
        """
        Create multiple records asynchronously.

        Args:
            data_list: List of attribute dictionaries
            commit: Whether to commit immediately

        Returns:
            List of created instances

        Example:
        ```python
            users = await repo.create_many([
                {'name': 'John', 'email': 'john@test.com'},
                {'name': 'Jane', 'email': 'jane@test.com'}
            ])
        ```
        """
        instances = [self.model(**data) for data in data_list]
        self.session.add_all(instances)

        if commit:
            await self.session.commit()
            for instance in instances:
                await self.session.refresh(instance)

        return instances

    # ========================================================================
    # READ
    # ========================================================================

    async def get(self, id: Any, load_relations: list[str] | None = None) -> T | None:
        """
        Get record by primary key asynchronously.

        Excludes soft-deleted records by default.

        Args:
            id: Primary key value
            load_relations: List of relationship names to eager load (prevents N+1)


        Returns:
            Model instance or None if not found or soft-deleted

        Example:
        ```python
            user = await repo.get(1)
        ```
        """
        query = select(self.model).where(self.model.id == id)

        if load_relations:
            query = self._apply_eager_loading(query, load_relations)

        if self._has_soft_delete():
            query = query.where(self.model.deleted_at.is_(None))

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_or_404(self, id: Any, load_relations: list[str] | None = None  ) -> T:
        """
        Get record by ID or raise exception asynchronously.

        Args:
            id: Primary key value
            load_relations: List of relationship names to eager load

        Returns:
            Model instance

        Raises:
            ValueError: If record not found

        Example:
        ```python
            user = await repo.get_or_404(1)
        ```
        """
        instance = await self.get(id, load_relations=load_relations)
        if instance is None:
            raise ValueError(f"{self.model.__name__} with id={id} not found")
        return instance

    async def get_all(self, limit: int | None = None, load_relations: list[str] | None = None) -> list[T]:
        """
        Get all records asynchronously.

        Args:
            limit: Maximum number of records to return
            load_relations: List of relationship names to eager load

        Returns:
            List of model instances

        Example:
        ```python
            all_users = await repo.get_all()
            first_100 = await repo.get_all(limit=100)
        ```
        """
        query = select(self.model)

        if load_relations:
            query = self._apply_eager_loading(query, load_relations)

        if self._has_soft_delete():
            query = query.where(self.model.deleted_at.is_(None))

        if limit:
            query = query.limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def filter(
            self,
            _limit: int | None = None,
            _offset: int | None = None,
            _order_by: str | None = None,
            _load_relations: list[str] | None = None,
            **filters
    ) -> list[T]:
        """
        Filter records with operator support asynchronously.

        Supports Django-style field lookups:
        - field__operator=value

        Operators:
        - eq: Equal (default if no operator)
        - ne: Not equal
        - lt, lte, gt, gte: Comparisons
        - in, not_in: IN/NOT IN lists
        - like, ilike: LIKE patterns
        - is_null: IS NULL (pass True/False)
        - is_not_null: IS NOT NULL
        - between: BETWEEN (pass tuple/list of 2 values)
        - startswith, endswith, contains: String patterns

        Examples:
        ```python
            # Simple equality
            await repo.filter(status='active')

            # With operators
            await repo.filter(age__gte=18, age__lt=65)
            await repo.filter(email__ilike='%@gmail.com')
            await repo.filter(status__in=['active', 'pending'])
            await repo.filter(deleted_at__is_null=True)
            await repo.filter(price__between=(10, 100))
            await repo.filter(name__startswith='John')

            # With pagination
            await repo.filter(status='active', _limit=10, _offset=20)

            # With ordering
            await repo.filter(age__gte=18, _order_by='name')  # ASC
            await repo.filter(age__gte=18, _order_by='-created_at')  # DESC
        ```
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

        if _load_relations:
            query = self._apply_eager_loading(query, _load_relations)

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

        # Apply offset
        if _offset:
            query = query.offset(_offset)

        # Apply limit
        if _limit:
            query = query.limit(_limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def first(self,
                    _order_by: str | None = None,
                    _load_relations: list[str] | None = None,
                    **filters) -> T | None:
        """
        Get first record matching filters asynchronously.

        Args:
            _order_by: Order by field
            _load_relations: List of relationship names to eager load
            **filters: Filter conditions

        Returns:
            First matching record or None

        Example:
        ```python
            user = await repo.first(email='john@test.com')
            newest = await repo.first(_order_by='-created_at')
        ```
        """
        results = await self.filter(_limit=1, _order_by=_order_by, _load_relations=_load_relations, **filters)
        return results[0] if results else None

    async def exists(self, **filters) -> bool:
        """
        Check if any records match filters asynchronously.

        Args:
            **filters: Filter conditions

        Returns:
            True if any records exist

        Example:
        ```python
            exists = await repo.exists(email='john@test.com')
        ```
        """
        count = await self.count(**filters)
        return count > 0

    async def count(self, **filters) -> int:
        """
        Count records matching filters asynchronously.

        Args:
            **filters: Filter conditions

        Returns:
            Number of matching records

        Example:
        ```python
            total_active = await repo.count(status='active')
        ```
        """
        query = select(func.count()).select_from(self.model)

        if self._has_soft_delete():
            query = query.where(self.model.deleted_at.is_(None))

        # Build WHERE conditions
        conditions = []
        for key, value in filters.items():
            self._parse_field_operator(key, value, conditions)

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.session.execute(query)
        return result.scalar() or 0

    # ========================================================================
    # UPDATE
    # ========================================================================

    async def update(
            self,
            id: Any,
            data: dict[str, Any],
            commit: bool = True
    ) -> T | None:
        """
        Update record by ID asynchronously.

        Args:
            id: Primary key value
            data: Dictionary of attributes to update
            commit: Whether to commit immediately

        Returns:
            Updated instance or None if not found

        Example:
        ```python
            user = await repo.update(1, {'name': 'Jane'})
        ```
        """
        instance = await self.get(id)

        if instance is None:
            return None

        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)

        if commit:
            await self.session.commit()
            await self.session.refresh(instance)

        return instance

    async def update_many(
            self,
            filters: dict[str, Any],
            data: dict[str, Any],
            commit: bool = True
    ) -> int:
        """
        Update multiple records matching filters asynchronously.

        Args:
            filters: Filter conditions
            data: Data to update
            commit: Whether to commit immediately

        Returns:
            Number of updated records

        Example:
        ```python
            # Deactivate all banned users
            count = await repo.update_many(
                filters={'status': 'banned'},
                data={'active': False}
            )
        ```
        """
        instances = await self.filter(**filters)

        for instance in instances:
            for key, value in data.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)

        if commit:
            await self.session.commit()

        return len(instances)

    # ========================================================================
    # DELETE
    # ========================================================================

    async def delete(self, id: Any, commit: bool = True, force: bool = False) -> bool:
        """
        Delete record by ID asynchronously.

        Uses soft delete if available, unless force=True.

        Args:
            id: Primary key value
            commit: Whether to commit immediately
            force: Force hard delete even if soft delete available

        Returns:
            True if deleted, False if not found

        Example:
        ```python
            # Soft delete (if available)
            deleted = await repo.delete(1)

            # Force hard delete
            deleted = await repo.delete(1, force=True)
        ```
        """
        instance = await self.get(id)

        if instance is None:
            return False

        if hasattr(instance, 'soft_delete') and not force:
            instance.soft_delete()
        else:
            await self.session.delete(instance)

        if commit:
            await self.session.commit()

        return True

    async def delete_many(
            self,
            filters: dict[str, Any],
            commit: bool = True,
            force: bool = False
    ) -> int:
        """
        Delete multiple records matching filters asynchronously.

        Args:
            filters: Filter conditions
            commit: Whether to commit immediately
            force: Force hard delete

        Returns:
            Number of deleted records

        Example:
        ```python
            # Delete all inactive users
            count = await repo.delete_many({'active': False})
        ```
        """
        instances = await self.filter(**filters)

        for instance in instances:
            if hasattr(instance, 'soft_delete') and not force:
                instance.soft_delete()
            else:
                await self.session.delete(instance)

        if commit:
            await self.session.commit()

        return len(instances)

    # ========================================================================
    # PAGINATION
    # ========================================================================

    async def paginate(
            self,
            page: int = 1,
            per_page: int = 20,
            _order_by: str | None = None,
            _load_relations: list[str] | None = None,
            **filters
    ) -> tuple[list[T], dict[str, Any]]:
        """
        Paginate records with metadata asynchronously.

        Excludes soft-deleted records by default.

        Args:
            page: Page number (1-indexed)
            per_page: Items per page
            _order_by: Order by field (prefix with - for DESC)
            _load_relations: Relationships to eager load (prevents N+1)
            **filters: Filter conditions with operators

        Returns:
            Tuple of (items, metadata)

        Example:
        ```python
            # Page 2, 20 items per page, sorted by created_at descending
            users, meta = await repo.paginate(
                page=2,
                per_page=20,
                _order_by='-created_at',
                is_active=True
            )

            # meta = {
            #     'page': 2,
            #     'per_page': 20,
            #     'total': 150,
            #     'total_pages': 8,
            #     'has_next': True,
            #     'has_prev': True
            # }
        ```
        """
        # Get total count (with filters)
        total = await self.count(**filters)

        # Calculate pagination metadata
        total_pages = (total + per_page - 1) // per_page if total > 0 else 0
        offset = (page - 1) * per_page

        # Get items with limit, offset, and ordering
        items = await self.filter(
            _limit=per_page,
            _offset=offset,
            _order_by=_order_by,
            _load_relations=_load_relations,
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

    async def refresh(self, instance: T) -> T:
        """
        Refresh instance from database asynchronously.

        Args:
            instance: Model instance to refresh

        Returns:
            Refreshed instance

        Example:
        ```python
            user = await repo.refresh(user)
        ```
        """
        await self.session.refresh(instance)
        return instance

    async def commit(self) -> None:
        """Commit current transaction asynchronously."""
        await self.session.commit()

    async def rollback(self) -> None:
        """Rollback current transaction asynchronously."""
        await self.session.rollback()

    async def flush(self) -> None:
        """Flush pending changes asynchronously."""
        await self.session.flush()

    def _parse_field_operator(self, key: str, value: Any, conditions: list[Any]):
        """Parse field__operator format and build condition."""
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
# Async Repository Factory
# ============================================================================

def create_async_repository(model: Type[T], session: AsyncSession) -> AsyncRepository[T]:
    """
    Factory function to create async repository.

    Args:
        model: SQLAlchemy model class
        session: Async database session

    Returns:
        AsyncRepository instance

    Example:
    ```python
        from fastkit_core.database import create_async_repository
        from sqlalchemy.ext.asyncio import AsyncSession

        user_repo = create_async_repository(User, session)
        post_repo = create_async_repository(Post, session)

        # Use it
        users = await user_repo.get_all()
        user = await user_repo.create({'name': 'John'})
    ```
    """
    return AsyncRepository(model, session)