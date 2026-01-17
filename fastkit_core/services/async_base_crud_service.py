"""
Async Base CRUD Service Layer

Provides async business logic layer on top of async repository pattern.
Handles validation, transactions, lifecycle hooks, and response mapping.
"""

from typing import Any, Generic, TypeVar, Optional, Type
from abc import ABC

from fastkit_core.database import AsyncRepository

# Type variables
ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")
ResponseSchemaType = TypeVar("ResponseSchemaType")


class AsyncBaseCrudService(
    Generic[ModelType, CreateSchemaType, UpdateSchemaType, ResponseSchemaType],
    ABC
):
    """
    Async base CRUD service providing business logic layer.

    Features:
    - Async validation hooks
    - Async lifecycle hooks (before/after)
    - Transaction control
    - Error handling
    - Schema to dict conversion
    - Automatic response mapping (optional)

    Example:
        class UserService(AsyncBaseCrudService[
            User,           # Model
            UserCreate,     # Create schema
            UserUpdate,     # Update schema
            UserResponse    # Response schema
        ]):
            def __init__(self, repository: AsyncRepository):
                super().__init__(repository, response_schema=UserResponse)

            async def validate_create(self, data: UserCreate) -> None:
                if await self.exists(email=data.email):
                    raise ValueError("Email already exists")

        # Usage - automatic response mapping
        user_response: UserResponse = await user_service.create(user_data)
        # Returns UserResponse, not User model!

        # Without response mapping
        user_service = UserService(repo, response_schema=None)
        user_model: User = await user_service.create(user_data)
        # Returns User model
    """

    def __init__(
        self,
        repository: AsyncRepository,
        response_schema: Type[ResponseSchemaType] | None = None
    ):
        """
        Initialize service with async repository.

        Args:
            repository: AsyncRepository instance for database operations
            response_schema: Optional Pydantic schema for response mapping
                           If provided, all methods will return this schema instead of model

        Example:
            # With response mapping
            service = UserService(repo, response_schema=UserResponse)
            user = await service.create(data)  # Returns UserResponse

            # Without response mapping
            service = UserService(repo)
            user = await service.create(data)  # Returns User model
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
        """
        Convert model instance to response schema.

        Args:
            instance: Model instance or None

        Returns:
            Response schema instance, model instance, or None
        """
        if instance is None:
            return None

        if self.response_schema is None:
            return instance

        # Convert model to response schema
        return self._map_to_response(instance)

    def _to_response_list(
        self,
        instances: list[ModelType]
    ) -> list[ResponseSchemaType] | list[ModelType]:
        """
        Convert list of model instances to response schemas.

        Args:
            instances: List of model instances

        Returns:
            List of response schemas or models
        """
        if self.response_schema is None:
            return instances

        return [self._map_to_response(instance) for instance in instances]

    def _map_to_response(self, instance: ModelType) -> ResponseSchemaType:
        """
        Map model instance to response schema.

        Supports both Pydantic v1 and v2.

        Args:
            instance: Model instance

        Returns:
            Response schema instance
        """
        # Try Pydantic v2 (model_validate)
        if hasattr(self.response_schema, 'model_validate'):
            return self.response_schema.model_validate(instance)

        # Try Pydantic v1 (from_orm)
        if hasattr(self.response_schema, 'from_orm'):
            return self.response_schema.from_orm(instance)

        # Fallback: try direct instantiation
        return self.response_schema(**instance.__dict__)

    # ========================================================================
    # Validation Hooks (Override in subclasses)
    # ========================================================================

    async def validate_create(self, data: CreateSchemaType) -> None:
        """
        Validate data before creation (async).

        Override this to add custom validation logic.
        Raise ValueError or custom exception if validation fails.

        Args:
            data: Data to validate

        Raises:
            ValueError: If validation fails

        Example:
            async def validate_create(self, data: UserCreate) -> None:
                if await self.exists(email=data.email):
                    raise ValueError("Email already exists")
        """
        pass

    async def validate_update(self, id: Any, data: UpdateSchemaType) -> None:
        """
        Validate data before update (async).

        Override this to add custom validation logic.

        Args:
            id: Record ID being updated
            data: Data to validate

        Raises:
            ValueError: If validation fails

        Example:
            async def validate_update(self, id: int, data: UserUpdate) -> None:
                user = await self.find(id)
                if user and data.email and data.email != user.email:
                    if await self.exists(email=data.email):
                        raise ValueError("Email already exists")
        """
        pass

    # ========================================================================
    # Lifecycle Hooks (Override in subclasses)
    # ========================================================================

    async def before_create(self, data: dict) -> dict:
        """
        Modify data before creation (async).

        Override this to transform data before saving.

        Args:
            data: Data dictionary

        Returns:
            Modified data dictionary

        Example:
            async def before_create(self, data: dict) -> dict:
                data['password'] = await hash_password(data['password'])
                data['verified_at'] = await check_email_verification(data['email'])
                return data
        """
        return data

    async def after_create(self, instance: ModelType) -> None:
        """
        Perform actions after creation (async).

        Override this for post-creation logic (emails, events, etc.).

        Args:
            instance: Created model instance

        Example:
            async def after_create(self, instance: User) -> None:
                await send_welcome_email(instance.email)
                await publish_event('user.created', instance.id)
        """
        pass

    async def before_update(self, id: Any, data: dict) -> dict:
        """
        Modify data before update (async).

        Args:
            id: Record ID being updated
            data: Data dictionary

        Returns:
            Modified data dictionary

        Example:
            async def before_update(self, id: int, data: dict) -> dict:
                if 'password' in data:
                    data['password'] = await hash_password(data['password'])
                return data
        """
        return data

    async def after_update(self, instance: ModelType) -> None:
        """
        Perform actions after update (async).

        Args:
            instance: Updated model instance

        Example:
            async def after_update(self, instance: User) -> None:
                await invalidate_cache(f'user:{instance.id}')
                await publish_event('user.updated', instance.id)
        """
        pass

    async def before_delete(self, id: Any) -> None:
        """
        Perform checks before deletion (async).

        Args:
            id: Record ID to delete

        Raises:
            ValueError: If deletion should be prevented

        Example:
            async def before_delete(self, id: int) -> None:
                user = await self.find(id)
                if user and user.is_admin:
                    raise ValueError("Cannot delete admin users")
        """
        pass

    async def after_delete(self, id: Any) -> None:
        """
        Perform actions after deletion (async).

        Args:
            id: Deleted record ID

        Example:
            async def after_delete(self, id: int) -> None:
                await cleanup_user_data(id)
                await publish_event('user.deleted', id)
        """
        pass

    # ========================================================================
    # READ Operations
    # ========================================================================

    async def find(
        self,
        id: Any,
        load_relations: list[str] | None = None,
    ) -> Optional[ResponseSchemaType] | Optional[ModelType]:
        """
        Find record by ID (async).

        Args:
            id: Primary key value
            load_relations: List of relationship names to eager load
        Returns:
            Response schema or model instance, or None if not found

        Example:
            # With response_schema
            user: UserResponse = await service.find(1)

            # Without response_schema
            user: User = await service.find(1)
        """
        instance = await self.repository.get(id, load_relations=load_relations)
        return self._to_response(instance)

    async def find_or_fail(
        self,
        id: Any,
        load_relations: list[str] | None = None,
    ) -> ResponseSchemaType | ModelType:
        """
        Find record by ID or raise exception (async).

        Args:
            id: Primary key value
            load_relations: List of relationship names to eager load
        Returns:
            Response schema or model instance

        Raises:
            ValueError: If record not found

        Example:
            user: UserResponse = await service.find_or_fail(1)
        """
        instance = await self.repository.get(id, load_relations=load_relations)
        if instance is None:
            model_name = self.repository.model.__name__
            raise ValueError(f"{model_name} with id={id} not found")
        return self._to_response(instance)

    async def get_all(
            self,
            limit: int | None = None,
            load_relations: list[str] | None = None
    ) -> list[ResponseSchemaType] | list[ModelType]:
        """
        Get all records (async).

        Args:
            load_relations:  List of relations
            limit: Maximum number of records

        Returns:
            List of response schemas or model instances

        Example:
            users: list[UserResponse] = await service.get_all(limit=100)
        """
        instances = await self.repository.get_all(limit=limit, load_relations=load_relations)
        return self._to_response_list(instances)

    async def filter(
        self,
        _limit: int | None = None,
        _offset: int | None = None,
        _order_by: str | None = None,
        _load_relations: list[str] | None = None,
        **filters
    ) -> list[ResponseSchemaType] | list[ModelType]:
        """
        Filter records with operator support (async).

        Supports Django-style operators (field__gte, field__in, etc.).

        Args:
            _load_relations: List of relations
            _limit: Limit number of results
            _offset: Offset for pagination
            _order_by: Order by field (prefix with - for DESC)
            **filters: Filter conditions with operators

        Returns:
            List of response schemas or model instances

        Example:
            adults: list[UserResponse] = await service.filter(
                age__gte=18,
                status='active',
                _order_by='-created_at'
            )
        """
        instances = await self.repository.filter(
            _limit=_limit,
            _offset=_offset,
            _order_by=_order_by,
            _load_relations=_load_relations,
            **filters
        )
        return self._to_response_list(instances)

    async def filter_one(
        self,
        load_relations: list[str] | None = None,
        **filters
    ) -> Optional[ResponseSchemaType] | Optional[ModelType]:
        """
        Get first record matching filters (async).

        Args:
            load_relations: List of relationship names to eager load
            **filters: Filter conditions with operators

        Returns:
            Response schema or model instance, or None

        Example:
            user: UserResponse | None = await service.filter_one(email='john@example.com')
        """
        results = await self.repository.filter(_limit=1, _load_relations=load_relations, **filters)
        instance = results[0] if results else None
        return self._to_response(instance)

    async def paginate(
        self,
        page: int = 1,
        per_page: int = 20,
        _order_by: str | None = None,
        _load_relations: list[str] | None = None,
        **filters
    ) -> tuple[
        list[ResponseSchemaType] | list[ModelType],
        dict[str, Any]
    ]:
        """
        Paginate records with operator support (async).

        Args:
            _load_relations: List of relations
            page: Page number (1-indexed)
            per_page: Items per page
            _order_by: Order by field (prefix with - for DESC)
            **filters: Filter conditions with operators

        Returns:
            Tuple of (response schemas or models, metadata)

        Example:
            users, meta = await service.paginate(
                page=1,
                per_page=20,
                is_active=True,
                _order_by='-created_at'
            )
            # users: list[UserResponse]
            # meta: {'page': 1, 'per_page': 20, 'total': 100, ...}
        """
        instances, metadata = await self.repository.paginate(
            page=page,
            per_page=per_page,
            _order_by=_order_by,
            _load_relations=_load_relations,
            **filters
        )
        return self._to_response_list(instances), metadata

    async def exists(self, **filters) -> bool:
        """
        Check if record exists (async).

        Args:
            **filters: Filter conditions

        Returns:
            True if exists, False otherwise

        Example:
            exists = await service.exists(email='john@example.com')
        """
        return await self.repository.exists(**filters)

    async def count(self, **filters) -> int:
        """
        Count records matching filters (async).

        Args:
            **filters: Filter conditions with operators

        Returns:
            Number of matching records

        Example:
            total_active = await service.count(is_active=True)
        """
        return await self.repository.count(**filters)

    # ========================================================================
    # CREATE Operations
    # ========================================================================

    async def create(
        self,
        data: CreateSchemaType,
        commit: bool = True
    ) -> ResponseSchemaType | ModelType:
        """
        Create a new record with validation and hooks (async).

        Args:
            data: Data to create (Pydantic model or dict)
            commit: Whether to commit transaction

        Returns:
            Response schema or model instance

        Raises:
            ValueError: If validation fails

        Example:
            # With response_schema
            user_data = UserCreate(name='John', email='john@example.com')
            user: UserResponse = await service.create(user_data)

            # Without response_schema
            user: User = await service.create(user_data)
        """
        # Validation hook
        await self.validate_create(data)

        # Convert to dict
        data_dict = self._to_dict(data)

        # Before create hook
        data_dict = await self.before_create(data_dict)

        # Create
        instance = await self.repository.create(data=data_dict, commit=commit)

        # After create hook
        if commit:
            await self.after_create(instance)

        return self._to_response(instance)

    async def create_many(
        self,
        data_list: list[CreateSchemaType],
        commit: bool = True
    ) -> list[ResponseSchemaType] | list[ModelType]:
        """
        Create multiple records (async).

        Args:
            data_list: List of data to create
            commit: Whether to commit transaction

        Returns:
            List of response schemas or model instances

        Example:
            users_data = [
                UserCreate(name='John', email='john@example.com'),
                UserCreate(name='Jane', email='jane@example.com')
            ]
            users: list[UserResponse] = await service.create_many(users_data)
        """
        # Convert all to dicts
        dict_list = [self._to_dict(data) for data in data_list]

        # Validate all
        for data in data_list:
            await self.validate_create(data)

        # Apply before_create to all
        processed_dicts = []
        for d in dict_list:
            processed = await self.before_create(d)
            processed_dicts.append(processed)

        # Create
        instances = await self.repository.create_many(
            data_list=processed_dicts,
            commit=commit
        )

        # After create hooks
        if commit:
            for instance in instances:
                await self.after_create(instance)

        return self._to_response_list(instances)

    # ========================================================================
    # UPDATE Operations
    # ========================================================================

    async def update(
        self,
        id: Any,
        data: UpdateSchemaType,
        commit: bool = True
    ) -> Optional[ResponseSchemaType] | Optional[ModelType]:
        """
        Update record by ID with validation and hooks (async).

        Args:
            id: Primary key value
            data: Data to update
            commit: Whether to commit transaction

        Returns:
            Response schema, model instance, or None if not found

        Raises:
            ValueError: If validation fails

        Example:
            user_data = UserUpdate(name='Jane Doe')
            user: UserResponse = await service.update(1, user_data)
        """
        # Validation hook
        await self.validate_update(id, data)

        # Convert to dict
        data_dict = self._to_dict(data)

        # Before update hook
        data_dict = await self.before_update(id, data_dict)

        # Update
        instance = await self.repository.update(id=id, data=data_dict, commit=commit)

        # After update hook
        if instance and commit:
            await self.after_update(instance)

        return self._to_response(instance)

    async def update_many(
        self,
        filters: dict[str, Any],
        data: UpdateSchemaType,
        commit: bool = True
    ) -> int:
        """
        Update multiple records matching filters (async).

        Args:
            filters: Filter conditions
            data: Data to update
            commit: Whether to commit transaction

        Returns:
            Number of updated records

        Example:
            count = await service.update_many(
                filters={'is_active': False},
                data=UserUpdate(status='inactive')
            )
        """
        data_dict = self._to_dict(data)
        return await self.repository.update_many(
            filters=filters,
            data=data_dict,
            commit=commit
        )

    # ========================================================================
    # DELETE Operations
    # ========================================================================

    async def delete(self, id: Any, commit: bool = True, force: bool = False) -> bool:
        """
        Delete record by ID (async).

        Args:
            id: Primary key value
            commit: Whether to commit transaction
            force: If soft delete is enabled this flag will force delete record

        Returns:
            True if deleted, False if not found

        Example:
            deleted = await service.delete(1)
            # For hard delete (skip soft delete)
            deleted = await service.delete(1, force=True)
        """
        # Before delete hook
        await self.before_delete(id)

        # Delete
        deleted = await self.repository.delete(id=id, commit=commit, force=force)

        # After delete hook
        if deleted and commit:
            await self.after_delete(id)

        return deleted

    async def delete_many(
        self,
        filters: dict[str, Any],
        commit: bool = True
    ) -> int:
        """
        Delete multiple records matching filters (async).

        Args:
            filters: Filter conditions
            commit: Whether to commit transaction

        Returns:
            Number of deleted records

        Example:
            count = await service.delete_many({'is_active': False})
        """
        return await self.repository.delete_many(filters=filters, commit=commit)

    # ========================================================================
    # Transaction Management
    # ========================================================================

    async def commit(self) -> None:
        """
        Commit current transaction (async).

        Example:
            await service.create(user_data, commit=False)
            await service.create(profile_data, commit=False)
            await service.commit()  # Commit both
        """
        await self.repository.commit()

    async def rollback(self) -> None:
        """
        Rollback current transaction (async).

        Example:
            try:
                await service.create(user_data, commit=False)
                await service.create(profile_data, commit=False)
                await service.commit()
            except Exception:
                await service.rollback()
        """
        await self.repository.rollback()

    async def flush(self) -> None:
        """
        Flush pending changes (async).

        Example:
            user = await service.create(user_data, commit=False)
            await service.flush()  # Get ID without committing
            print(user.id)  # Now available
        """
        await self.repository.flush()