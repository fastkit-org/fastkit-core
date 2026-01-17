"""
Base CRUD Service Layer

Provides business logic layer on top of repository pattern.
Handles validation, transactions, lifecycle hooks, and response mapping.
"""

from typing import Any, Generic, TypeVar, Optional, Type
from abc import ABC

from fastkit_core.database import Repository

# Type variables
ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")
ResponseSchemaType = TypeVar("ResponseSchemaType")


class BaseCrudService(
    Generic[ModelType, CreateSchemaType, UpdateSchemaType, ResponseSchemaType],
    ABC
):
    """
    Base CRUD service providing business logic layer.

    Features:
    - Validation hooks
    - Lifecycle hooks (before/after)
    - Transaction control
    - Error handling
    - Schema to dict conversion
    - Automatic response mapping (optional)

    Example:
        class UserService(BaseCrudService[
            User,           # Model
            UserCreate,     # Create schema
            UserUpdate,     # Update schema
            UserResponse    # Response schema
        ]):
            def __init__(self, repository: Repository):
                super().__init__(repository, response_schema=UserResponse)

            def validate_create(self, data: UserCreate) -> None:
                if self.exists(email=data.email):
                    raise ValueError("Email already exists")

        # Usage - automatic response mapping
        user_response: UserResponse = user_service.create(user_data)
        # Returns UserResponse, not User model!
    """

    def __init__(
        self,
        repository: Repository,
        response_schema: Type[ResponseSchemaType] | None = None
    ):
        """
        Initialize service with repository.

        Args:
            repository: Repository instance for database operations
            response_schema: Optional Pydantic schema for response mapping
        """
        self.repository = repository
        self.response_schema = response_schema

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

    def _to_response(
        self,
        instance: ModelType | None
    ) -> ResponseSchemaType | ModelType | None:
        """Convert model instance to response schema."""
        if instance is None:
            return None

        if self.response_schema is None:
            return instance

        return self._map_to_response(instance)

    def _to_response_list(
        self,
        instances: list[ModelType]
    ) -> list[ResponseSchemaType] | list[ModelType]:
        """Convert list of model instances to response schemas."""
        if self.response_schema is None:
            return instances

        return [self._map_to_response(instance) for instance in instances]

    def _map_to_response(self, instance: ModelType) -> ResponseSchemaType:
        """Map model instance to response schema."""
        if hasattr(self.response_schema, 'model_validate'):
            return self.response_schema.model_validate(instance)

        if hasattr(self.response_schema, 'from_orm'):
            return self.response_schema.from_orm(instance)

        return self.response_schema(**instance.__dict__)

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

    def find(self, id: Any,  load_relations: list[str] | None = None) -> Optional[ResponseSchemaType] | Optional[ModelType]:
        """Find record by ID."""
        instance = self.repository.get(id, load_relations=load_relations)
        return self._to_response(instance)

    def find_or_fail(self, id: Any, load_relations: list[str] | None = None,) -> ResponseSchemaType | ModelType:
        """Find record by ID or raise exception."""
        instance = self.repository.get(id, load_relations=load_relations)
        if instance is None:
            model_name = self.repository.model.__name__
            raise ValueError(f"{model_name} with id={id} not found")
        return self._to_response(instance)

    def get_all(self,
                limit: int | None = None,
                load_relations: list[str] | None = None
                ) -> list[ResponseSchemaType] | list[ModelType]:
        """Get all records."""
        instances = self.repository.get_all(limit=limit, load_relations=load_relations)
        return self._to_response_list(instances)

    def filter(
        self,
        _limit: int | None = None,
        _offset: int | None = None,
        _order_by: str | None = None,
        _load_relations: list[str] | None = None,
        **filters
    ) -> list[ResponseSchemaType] | list[ModelType]:
        """Filter records with operator support."""
        instances = self.repository.filter(
            _limit=_limit,
            _offset=_offset,
            _order_by=_order_by,
            _load_relations=_load_relations,
            **filters
        )
        return self._to_response_list(instances)

    def filter_one(self, _load_relations: list[str] | None = None, **filters) -> Optional[ResponseSchemaType] | Optional[ModelType]:
        """Get first record matching filters."""
        instance = self.repository.first(_load_relations=_load_relations, **filters)
        return self._to_response(instance)

    def paginate(
        self,
        page: int = 1,
        per_page: int = 20,
        _order_by: str | None = None,
        _load_relations: list[str] | None = None,
        **filters
    ) -> tuple[list[ResponseSchemaType] | list[ModelType], dict[str, Any]]:
        """Paginate records with operator support."""
        instances, metadata = self.repository.paginate(
            page=page,
            per_page=per_page,
            _order_by=_order_by,
            _load_relations=_load_relations,
            **filters
        )
        return self._to_response_list(instances), metadata

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
    ) -> ResponseSchemaType | ModelType:
        """Create a new record with validation and hooks."""
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

        return self._to_response(instance)

    def create_many(
        self,
        data_list: list[CreateSchemaType],
        commit: bool = True
    ) -> list[ResponseSchemaType] | list[ModelType]:
        """Create multiple records."""
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

        return self._to_response_list(instances)

    # ========================================================================
    # UPDATE Operations
    # ========================================================================

    def update(
        self,
        id: Any,
        data: UpdateSchemaType,
        commit: bool = True
    ) -> Optional[ResponseSchemaType] | Optional[ModelType]:
        """Update record by ID with validation and hooks."""
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

        return self._to_response(instance)

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