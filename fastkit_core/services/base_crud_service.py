"""
Base CRUD Service Layer

Provides business logic layer on top of repository pattern.
Handles validation, transactions, and lifecycle hooks.
"""

from typing import Any, Generic, TypeVar, Optional
from abc import ABC

from fastkit_core.database import Repository

# Type variables
ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")


class BaseCrudService(Generic[ModelType, CreateSchemaType, UpdateSchemaType], ABC):
    """
    Base CRUD service providing business logic layer.

    Features:
    - Validation hooks
    - Lifecycle hooks (before/after)
    - Transaction control
    - Error handling
    - Schema to dict conversion

    Example:
        class UserService(BaseCrudService[User, UserCreate, UserUpdate]):
            def __init__(self, repository: Repository):
                super().__init__(repository)

            def validate_create(self, data: UserCreate) -> None:
                # Custom validation
                if self.exists(email=data.email):
                    raise ValueError("Email already exists")

            def before_create(self, data: dict) -> dict:
                # Hash password before saving
                data['password'] = hash_password(data['password'])
                return data

            def after_create(self, instance: User) -> None:
                # Send welcome email
                send_welcome_email(instance.email)

        # Usage
        user_service = UserService(user_repository)
        user = user_service.create(user_data)
    """

    def __init__(self, repository: Repository):
        """
        Initialize service with repository.

        Args:
            repository: Repository instance for database operations
        """
        self.repository = repository

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _to_dict(self, data: Any) -> dict:
        """
        Convert Pydantic model or dict to dict.

        Supports both Pydantic v1 and v2.

        Args:
            data: Pydantic model, dict, or dict-like object

        Returns:
            Dictionary representation

        Raises:
            ValueError: If data type cannot be converted
        """
        if isinstance(data, dict):
            return data
        if hasattr(data, 'model_dump'):  # Pydantic v2
            return data.model_dump(exclude_unset=True)
        if hasattr(data, 'dict'):  # Pydantic v1
            return data.dict(exclude_unset=True)
        raise ValueError(f"Cannot convert {type(data)} to dict")

    # ========================================================================
    # Validation Hooks (Override in subclasses)
    # ========================================================================

    def validate_create(self, data: CreateSchemaType) -> None:
        """
        Validate data before creation.

        Override this to add custom validation logic.
        Raise ValueError or custom exception if validation fails.

        Args:
            data: Data to validate

        Raises:
            ValueError: If validation fails
        """
        pass

    def validate_update(self, id: Any, data: UpdateSchemaType) -> None:
        """
        Validate data before update.

        Override this to add custom validation logic.

        Args:
            id: Record ID being updated
            data: Data to validate

        Raises:
            ValueError: If validation fails
        """
        pass

    # ========================================================================
    # Lifecycle Hooks (Override in subclasses)
    # ========================================================================

    def before_create(self, data: dict) -> dict:
        """
        Modify data before creation.

        Override this to transform data before saving.

        Args:
            data: Data dictionary

        Returns:
            Modified data dictionary
        """
        return data

    def after_create(self, instance: ModelType) -> None:
        """
        Perform actions after creation.

        Override this for post-creation logic (emails, events, etc.).

        Args:
            instance: Created model instance
        """
        pass

    def before_update(self, id: Any, data: dict) -> dict:
        """
        Modify data before update.

        Args:
            id: Record ID being updated
            data: Data dictionary

        Returns:
            Modified data dictionary
        """
        return data

    def after_update(self, instance: ModelType) -> None:
        """
        Perform actions after update.

        Args:
            instance: Updated model instance
        """
        pass

    def before_delete(self, id: Any) -> None:
        """
        Perform checks before deletion.

        Args:
            id: Record ID to delete

        Raises:
            ValueError: If deletion should be prevented
        """
        pass

    def after_delete(self, id: Any) -> None:
        """
        Perform actions after deletion.

        Args:
            id: Deleted record ID
        """
        pass

    # ========================================================================
    # READ Operations
    # ========================================================================

    def find(self, id: Any) -> Optional[ModelType]:
        """
        Find record by ID.

        Args:
            id: Primary key value

        Returns:
            Model instance or None if not found
        """
        return self.repository.get(id)

    def find_or_fail(self, id: Any) -> ModelType:
        """
        Find record by ID or raise exception.

        Args:
            id: Primary key value

        Returns:
            Model instance

        Raises:
            ValueError: If record not found
        """
        instance = self.repository.get(id)
        if instance is None:
            model_name = self.repository.model.__name__
            raise ValueError(f"{model_name} with id={id} not found")
        return instance

    def get_all(self, limit: int | None = None) -> list[ModelType]:
        """
        Get all records.

        Args:
            limit: Maximum number of records

        Returns:
            List of model instances
        """
        return self.repository.get_all(limit=limit)

    def filter(
        self,
        _limit: int | None = None,
        _offset: int | None = None,
        _order_by: str | None = None,
        **filters
    ) -> list[ModelType]:
        """
        Filter records with operator support.

        Supports Django-style operators (field__gte, field__in, etc.).

        Args:
            _limit: Limit number of results
            _offset: Offset for pagination
            _order_by: Order by field (prefix with - for DESC)
            **filters: Filter conditions with operators

        Returns:
            List of matching instances

        Example:
            service.filter(age__gte=18, status='active', _order_by='-created_at')
        """
        return self.repository.filter(
            _limit=_limit,
            _offset=_offset,
            _order_by=_order_by,
            **filters
        )

    def filter_one(self, **filters) -> Optional[ModelType]:
        """
        Get first record matching filters.

        Args:
            **filters: Filter conditions with operators

        Returns:
            First matching instance or None
        """
        return self.repository.filter_one(**filters)

    def paginate(
        self,
        page: int = 1,
        per_page: int = 20,
        **filters
    ) -> tuple[list[ModelType], dict[str, Any]]:
        """
        Paginate records with operator support.

        Args:
            page: Page number (1-indexed)
            per_page: Items per page
            **filters: Filter conditions with operators

        Returns:
            Tuple of (items, metadata)
        """
        return self.repository.paginate(page=page, per_page=per_page, **filters)

    def exists(self, **filters) -> bool:
        """
        Check if record exists.

        Args:
            **filters: Filter conditions

        Returns:
            True if exists, False otherwise
        """
        return self.repository.exists(**filters)

    def count(self, **filters) -> int:
        """
        Count records matching filters.

        Args:
            **filters: Filter conditions with operators

        Returns:
            Number of matching records
        """
        return self.repository.count(**filters)

    # ========================================================================
    # CREATE Operations
    # ========================================================================

    def create(
        self,
        data: CreateSchemaType,
        commit: bool = True
    ) -> ModelType:
        """
        Create a new record with validation and hooks.

        Args:
            data: Data to create (Pydantic model or dict)
            commit: Whether to commit transaction

        Returns:
            Created model instance

        Raises:
            ValueError: If validation fails
        """
        # Validation hook
        self.validate_create(data)

        # Convert to dict
        data_dict = self._to_dict(data)

        # Before create hook
        data_dict = self.before_create(data_dict)

        # Create
        instance = self.repository.create(data=data_dict, commit=commit)

        # After create hook
        if commit:
            self.after_create(instance)

        return instance

    def create_many(
        self,
        data_list: list[CreateSchemaType],
        commit: bool = True
    ) -> list[ModelType]:
        """
        Create multiple records.

        Args:
            data_list: List of data to create
            commit: Whether to commit transaction

        Returns:
            List of created instances
        """
        # Convert all to dicts
        dict_list = [self._to_dict(data) for data in data_list]

        # Validate all
        for data in data_list:
            self.validate_create(data)

        # Apply before_create to all
        dict_list = [self.before_create(d) for d in dict_list]

        # Create
        instances = self.repository.create_many(
            data_list=dict_list,
            commit=commit
        )

        # After create hooks
        if commit:
            for instance in instances:
                self.after_create(instance)

        return instances

    # ========================================================================
    # UPDATE Operations
    # ========================================================================

    def update(
        self,
        id: Any,
        data: UpdateSchemaType,
        commit: bool = True
    ) -> ModelType | None:
        """
        Update record by ID with validation and hooks.

        Args:
            id: Primary key value
            data: Data to update
            commit: Whether to commit transaction

        Returns:
            Updated instance or None if not found

        Raises:
            ValueError: If validation fails
        """
        # Validation hook
        self.validate_update(id, data)

        # Convert to dict
        data_dict = self._to_dict(data)

        # Before update hook
        data_dict = self.before_update(id, data_dict)

        # Update
        instance = self.repository.update(id=id, data=data_dict, commit=commit)

        # After update hook
        if instance and commit:
            self.after_update(instance)

        return instance

    def update_many(
        self,
        filters: dict[str, Any],
        data: UpdateSchemaType,
        commit: bool = True
    ) -> int:
        """
        Update multiple records matching filters.

        Args:
            filters: Filter conditions
            data: Data to update
            commit: Whether to commit transaction

        Returns:
            Number of updated records
        """
        data_dict = self._to_dict(data)
        return self.repository.update_many(
            filters=filters,
            data=data_dict,
            commit=commit
        )

    # ========================================================================
    # DELETE Operations
    # ========================================================================

    def delete(self, id: Any, commit: bool = True, force: bool = False) -> bool:
        """
        Delete record by ID.

        Args:
            id: Primary key value
            commit: Whether to commit transaction
            force: If soft delete is enabled this flag will force delete record

        Returns:
            True if deleted, False if not found
        """
        # Before delete hook
        self.before_delete(id)

        # Delete
        deleted = self.repository.delete(id=id, commit=commit, force=force)

        # After delete hook
        if deleted and commit:
            self.after_delete(id)

        return deleted

    def delete_many(
        self,
        filters: dict[str, Any],
        commit: bool = True
    ) -> int:
        """
        Delete multiple records matching filters.

        Args:
            filters: Filter conditions
            commit: Whether to commit transaction

        Returns:
            Number of deleted records
        """
        return self.repository.delete_many(filters=filters, commit=commit)